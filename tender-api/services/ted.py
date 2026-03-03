"""
TED (Tenders Electronic Daily) API client — European public procurement.
Uses the official TED API v3 — free, no API key required for search.
Base URL: https://api.ted.europa.eu/v3

Official docs: https://docs.ted.europa.eu/api/latest/index.html

NOTE (2026-03): API v3 breaking changes vs previous version:
- `fields` is now REQUIRED and must use eForms field names (e.g. "notice-title")
- `language` parameter has been REMOVED
- Expert query field names changed: TD→notice-title, RD→deadline-receipt-tender-date-lot,
  CY→buyer-country, ND=CN* no longer supported (PREFIX removed for ND)
- Response key changed: `total` → `totalNoticeCount`
"""
import httpx
import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from models.notice import NoticeModel, BuyerModel
from services.boamp import cpv_to_sector, days_until

TED_API_BASE = "https://api.ted.europa.eu/v3/notices/search"
TED_NOTICE_URL = "https://ted.europa.eu/en/notice/{id}"

# Champs à récupérer dans chaque réponse TED (noms eForms v3)
TED_FIELDS = [
    "notice-identifier",
    "publication-number",
    "notice-title",
    "title-lot",
    "title-proc",
    "publication-date",
    "description-lot",
    "description-proc",
    "buyer-name",
    "buyer-city",
    "buyer-country",
    "classification-cpv",
    "deadline-receipt-tender-date-lot",
    "deadline-date-lot",
    "estimated-value-lot",
    "estimated-value-cur-lot",
    "procedure-type",
    "duration-period-value-lot",
]

# Mapping type de procédure TED → libellé FR
TED_PROCEDURE_MAP = {
    "open": "Ouverte",
    "restricted": "Restreinte",
    "negotiated-with-prior-publication": "Négociée avec publication",
    "competitive-dialogue": "Dialogue compétitif",
    "negotiated-without-prior-publication": "Négociée sans publication",
    "design-contest": "Conception",
    "innovation-partnership": "Partenariat d'innovation",
    # anciens codes numériques (compatibilité)
    "1": "Ouverte",
    "2": "Restreinte",
    "3": "Négociée avec publication",
    "4": "Dialogue compétitif",
    "5": "Négociée sans publication",
    "6": "Conception",
    "8": "Partenariat d'innovation",
}


def _pick_lang(obj: Any, langs: tuple = ("fra", "fre", "eng")) -> Optional[str]:
    """Extrait le texte d'un champ multilingue TED (dict {lang: str|list})."""
    if not obj:
        return None
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        for lang in langs:
            val = obj.get(lang)
            if val:
                if isinstance(val, list):
                    return val[0] if val else None
                return str(val)
        # fallback: première valeur disponible
        for val in obj.values():
            if val:
                if isinstance(val, list):
                    return val[0] if val else None
                return str(val)
    if isinstance(obj, list):
        return obj[0] if obj else None
    return None


def _first(lst: Any) -> Optional[Any]:
    """Retourne le premier élément d'une liste, ou la valeur elle-même."""
    if isinstance(lst, list):
        return lst[0] if lst else None
    return lst


def parse_ted_date(val: Any) -> Optional[str]:
    """Convertit une date TED (ISO 8601 avec ou sans Z) en chaîne ISO YYYY-MM-DD."""
    if not val:
        return None
    s = _first(val)
    if not s:
        return None
    s = str(s).rstrip("Z").split("T")[0]  # "2026-03-15Z" → "2026-03-15"
    # Tenter différents formats
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s[:10], fmt[:len(s[:10])]).date().isoformat()
        except ValueError:
            continue
    return s[:10] if len(s) >= 10 else s


def normalize_ted_record(notice: Dict[str, Any]) -> NoticeModel:
    """Convertit un avis TED API v3 (nouveaux noms eForms) en NoticeModel normalisé."""

    # ── ID & URL ──────────────────────────────────────────────────────────────
    notice_id = notice.get("notice-identifier") or ""
    publication_number = notice.get("publication-number") or notice_id
    url = TED_NOTICE_URL.format(id=publication_number)

    # ── Titre ─────────────────────────────────────────────────────────────────
    title = (
        _pick_lang(notice.get("title-proc"))
        or _pick_lang(notice.get("title-lot"))
        or _pick_lang(notice.get("notice-title"))
        or "Sans titre"
    )

    # ── Acheteur ──────────────────────────────────────────────────────────────
    buyer_name = _pick_lang(notice.get("buyer-name")) or None
    buyer_city = _pick_lang(notice.get("buyer-city")) or None
    buyer_country_raw = _pick_lang(notice.get("buyer-country")) or _first(notice.get("buyer-country")) or "EU"
    # TED retourne des codes 3 lettres (IRL, FRA…) — on garde tel quel
    buyer = BuyerModel(name=buyer_name, city=buyer_city, country=buyer_country_raw)

    # ── Dates ─────────────────────────────────────────────────────────────────
    pub_date = parse_ted_date(notice.get("publication-date"))
    deadline_raw = (
        notice.get("deadline-receipt-tender-date-lot")
        or notice.get("deadline-date-lot")
    )
    deadline = parse_ted_date(deadline_raw)

    # ── Budget ────────────────────────────────────────────────────────────────
    bmin = bmax = bdisplay = None
    val_raw = _first(notice.get("estimated-value-lot"))
    cur_raw = _first(notice.get("estimated-value-cur-lot")) or "EUR"
    if val_raw:
        try:
            amount = float(val_raw)
            bmin = bmax = amount
            bdisplay = f"{amount:,.0f} {cur_raw}".replace(",", " ")
        except (ValueError, TypeError):
            pass

    # ── CPV ───────────────────────────────────────────────────────────────────
    cpv_raw = notice.get("classification-cpv") or []
    if isinstance(cpv_raw, list):
        cpv_codes = [str(c).split("-")[0].strip() for c in cpv_raw if c]
    else:
        cpv_codes = [str(cpv_raw).split("-")[0].strip()] if cpv_raw else []

    cpv_labels = [cpv_to_sector(c) for c in cpv_codes]
    sector = cpv_labels[0] if cpv_labels else "Non classifié"

    # ── Type de procédure ─────────────────────────────────────────────────────
    proc_raw = _first(notice.get("procedure-type")) or ""
    procedure_type = TED_PROCEDURE_MAP.get(str(proc_raw).lower(), proc_raw) if proc_raw else None

    # ── Description ───────────────────────────────────────────────────────────
    description = (
        _pick_lang(notice.get("description-lot"))
        or _pick_lang(notice.get("description-proc"))
    )

    # ── Durée ─────────────────────────────────────────────────────────────────
    duration_months = None
    dur_raw = _first(notice.get("duration-period-value-lot"))
    if dur_raw:
        try:
            duration_months = int(float(str(dur_raw))) or None
        except (ValueError, TypeError):
            pass

    # ── Mots-clés depuis le titre ─────────────────────────────────────────────
    stop_words = {"of", "the", "and", "for", "with", "in", "to", "de", "du", "des", "le", "la", "les"}
    words = re.findall(r"\b[a-zA-ZÀ-ÿ]{4,}\b", title.lower())
    keywords = list(set(w for w in words if w not in stop_words))[:10]

    return NoticeModel(
        id=f"ted-{notice_id}",
        source="ted",
        title=title,
        buyer=buyer,
        publication_date=pub_date,
        deadline=deadline,
        deadline_days_remaining=days_until(deadline),
        budget_min=bmin,
        budget_max=bmax,
        budget_display=bdisplay,
        cpv_codes=cpv_codes,
        cpv_labels=cpv_labels,
        sector=sector,
        notice_type="Avis européen",
        procedure_type=procedure_type,
        description=description,
        url=url,
        keywords=keywords,
        duration_months=duration_months,
        raw_data=notice,
    )


async def search_ted(
    query: Optional[str] = None,
    cpv_prefix: Optional[str] = None,
    cpv_prefixes: Optional[List[str]] = None,
    limit: int = 20,
    page: int = 1,
    only_active: bool = True,
    country: Optional[str] = None,
) -> tuple[int, List[NoticeModel]]:
    """
    Recherche dans TED via l'API v3 (nouveaux noms de champs eForms).
    Retourne (total, liste_d'avis_normalisés).
    """
    query_parts = []

    if query:
        # Recherche dans le titre — guillemets pour expressions multi-mots
        clean = query.strip()
        if " " in clean:
            query_parts.append(f'notice-title ~ "{clean}"')
        else:
            query_parts.append(f'notice-title ~ {clean}')

    # CPV filter: supporte un ou plusieurs préfixes via OR de plages numériques
    all_cpv = cpv_prefixes or ([cpv_prefix] if cpv_prefix else [])
    if all_cpv:
        range_parts = []
        for p in all_cpv:
            try:
                low = int(p) * 1_000_000
                high = low + 999_999
                range_parts.append(f'(classification-cpv >= {low} AND classification-cpv <= {high})')
            except (ValueError, TypeError):
                pass
        if range_parts:
            combined = range_parts[0] if len(range_parts) == 1 else '(' + ' OR '.join(range_parts) + ')'
            query_parts.append(combined)

    if only_active:
        today = date.today().strftime("%Y%m%d")
        query_parts.append(f'deadline-receipt-tender-date-lot >= {today}')

    if country:
        query_parts.append(f'buyer-country = {country.upper()}')

    # Par défaut : avis récents des 30 derniers jours
    if not query_parts:
        from datetime import timedelta
        thirty_days_ago = (date.today() - timedelta(days=30)).strftime("%Y%m%d")
        query_parts.append(f'publication-date >= {thirty_days_ago}')

    expert_query = " AND ".join(query_parts)

    payload = {
        "query": expert_query,
        "page": page,
        "limit": min(limit, 100),
        "scope": "ALL",
        "fields": TED_FIELDS,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(TED_API_BASE, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return 0, []

    total = data.get("totalNoticeCount", 0)
    notices_raw = data.get("notices", [])

    notices = []
    for raw in notices_raw:
        try:
            notices.append(normalize_ted_record(raw))
        except Exception:
            continue

    return total, notices


async def get_ted_notice(notice_id: str) -> Optional[NoticeModel]:
    """Récupère un avis TED par son numéro de publication."""
    payload = {
        "query": f'notice-identifier = {notice_id}',
        "page": 1,
        "limit": 1,
        "scope": "ALL",
        "fields": TED_FIELDS,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(TED_API_BASE, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None

    notices_raw = data.get("notices", [])
    if not notices_raw:
        return None
    try:
        return normalize_ted_record(notices_raw[0])
    except Exception:
        return None
