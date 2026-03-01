"""
BOAMP (Bulletin Officiel des Annonces des Marchés Publics) API client.
Uses the official Opendatasoft API — free, no API key required.
Base URL: https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records

Official docs: https://www.boamp.fr/pages/donnees-ouvertes-et-api/
"""
import httpx
import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from models.notice import NoticeModel, BuyerModel

BOAMP_API_BASE = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records"
BOAMP_NOTICE_URL = "https://www.boamp.fr/avis/detail/{id}"

# CPV code prefix → sector mapping (simplified)
CPV_SECTOR_MAP = {
    "03": "Agriculture, Pêche",
    "09": "Energie",
    "14": "Mines, Extraction",
    "15": "Alimentaire",
    "16": "Machinerie Agricole",
    "18": "Vêtements, Textile",
    "19": "Cuir",
    "22": "Imprimerie, Publications",
    "24": "Chimie, Pharmacie",
    "30": "Informatique, Bureautique",
    "31": "Electrique, Electronique",
    "32": "Télécommunications",
    "33": "Médical, Santé",
    "34": "Transport, Véhicules",
    "35": "Sécurité, Défense",
    "37": "Sport, Loisirs",
    "38": "Instruments, Optique",
    "39": "Mobilier, Equipements",
    "41": "Eau",
    "42": "Industrie",
    "43": "Mines, Construction Equip",
    "44": "Construction, Matériaux",
    "45": "Travaux de Construction",
    "48": "Logiciels",
    "50": "Maintenance, Réparation",
    "51": "Installation",
    "55": "Hôtellerie, Restauration",
    "60": "Transport",
    "63": "Logistique",
    "64": "Postes, Télécommunications",
    "65": "Utilities (Eau, Gaz, Elec)",
    "66": "Assurance, Finance",
    "70": "Immobilier",
    "71": "Architecture, Ingénierie",
    "72": "Informatique, Services IT",
    "73": "R&D",
    "75": "Administration Publique",
    "76": "Pétrolier",
    "77": "Environnement, Jardinage",
    "79": "Services aux Entreprises",
    "80": "Formation, Education",
    "85": "Santé, Social",
    "90": "Assainissement, Déchets",
    "92": "Culture, Sport, Loisirs",
    "98": "Services divers",
}


def cpv_to_sector(cpv_code: str) -> str:
    """Map CPV code to sector label."""
    if not cpv_code:
        return "Non classifié"
    prefix = cpv_code[:2]
    return CPV_SECTOR_MAP.get(prefix, f"Secteur {prefix}xxx")


def parse_budget(fields: Dict[str, Any]) -> tuple[Optional[float], Optional[float], Optional[str]]:
    """Extract budget info from raw BOAMP fields."""
    montant = fields.get("montant") or fields.get("valeur_estimee")
    if montant:
        try:
            val = float(str(montant).replace(" ", "").replace(",", "."))
            return val, val, f"{val:,.0f} €".replace(",", " ")
        except (ValueError, TypeError):
            pass

    # Try to extract from text
    objet = fields.get("objet", "") or ""
    matches = re.findall(r"(\d[\d\s]*(?:[,\.]\d+)?)\s*(?:€|EUR|euros?)", objet, re.IGNORECASE)
    if matches:
        try:
            val = float(matches[0].replace(" ", "").replace(",", "."))
            return val, val, f"{val:,.0f} €".replace(",", " ")
        except (ValueError, TypeError):
            pass
    return None, None, None


def days_until(deadline_str: Optional[str]) -> Optional[int]:
    """Calculate days remaining until deadline."""
    if not deadline_str:
        return None
    try:
        dl = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
        remaining = (dl.date() - date.today()).days
        return max(remaining, 0)
    except (ValueError, TypeError):
        return None


def normalize_boamp_record(record: Dict[str, Any]) -> NoticeModel:
    """Convert a raw BOAMP API record into a normalized NoticeModel."""
    fields = record.get("fields", {}) or {}

    # IDs & URL
    notice_id = fields.get("idweb") or record.get("recordid") or ""
    url = BOAMP_NOTICE_URL.format(id=notice_id) if notice_id else None

    # Title
    title = fields.get("objet") or fields.get("libelle") or "Sans titre"

    # Buyer
    acheteur = fields.get("acheteur") or {}
    if isinstance(acheteur, str):
        buyer = BuyerModel(name=acheteur)
    elif isinstance(acheteur, dict):
        buyer = BuyerModel(
            name=acheteur.get("denomination") or acheteur.get("nom") or acheteur.get("name"),
            city=acheteur.get("ville") or acheteur.get("city"),
            country="FR"
        )
    else:
        buyer = BuyerModel(name=fields.get("nom_acheteur"))

    # Dates
    pub_date = fields.get("dateparution") or fields.get("date_parution")
    deadline = fields.get("datelimitereponse") or fields.get("date_limite_reponse")

    # Budget
    bmin, bmax, bdisplay = parse_budget(fields)

    # CPV
    cpv_raw = fields.get("cpv") or fields.get("codeCPV") or ""
    if isinstance(cpv_raw, list):
        cpv_codes = [str(c).strip() for c in cpv_raw if c]
    elif cpv_raw:
        cpv_codes = [str(cpv_raw).strip()]
    else:
        cpv_codes = []

    cpv_labels = [cpv_to_sector(c) for c in cpv_codes]
    sector = cpv_labels[0] if cpv_labels else cpv_to_sector("")

    # Notice/procedure type
    nature = fields.get("nature") or fields.get("type_marche")
    procedure = fields.get("procedure") or fields.get("type_procedure")

    # Description
    description_parts = []
    for key in ["descriptif", "description", "conditions_participation", "criteres_attribution"]:
        val = fields.get(key)
        if val and isinstance(val, str):
            description_parts.append(val.strip())
    description = " | ".join(description_parts) if description_parts else None

    # Duration
    duree_raw = fields.get("dureemois") or fields.get("duree_mois")
    duration_months = None
    if duree_raw:
        try:
            duration_months = int(duree_raw)
        except (ValueError, TypeError):
            pass

    # Keywords from title
    stop_words = {"de", "du", "des", "le", "la", "les", "un", "une", "et", "ou", "pour", "avec", "dans", "par"}
    words = re.findall(r"\b[a-zA-ZÀ-ÿ]{4,}\b", title.lower())
    keywords = list(set(w for w in words if w not in stop_words))[:10]

    return NoticeModel(
        id=f"boamp-{notice_id}",
        source="boamp",
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
        notice_type=nature,
        procedure_type=procedure,
        description=description,
        url=url,
        keywords=keywords,
        duration_months=duration_months,
        raw_data=fields,
    )


async def search_boamp(
    query: Optional[str] = None,
    cpv_prefix: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    only_active: bool = True,
) -> tuple[int, List[NoticeModel]]:
    """
    Search BOAMP notices.
    Returns (total_count, list_of_normalized_notices).
    """
    params: Dict[str, Any] = {
        "limit": min(limit, 100),
        "offset": offset,
        "order_by": "dateparution DESC",
        "lang": "fr",
    }

    # Build WHERE clause
    where_clauses = []

    if query:
        safe_q = query.replace('"', '\\"')
        where_clauses.append(f'search(objet, "{safe_q}")')

    if cpv_prefix:
        where_clauses.append(f'cpv like "{cpv_prefix}%"')

    if only_active:
        today = date.today().isoformat()
        where_clauses.append(f'datelimitereponse >= "{today}"')

    if where_clauses:
        params["where"] = " AND ".join(where_clauses)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(BOAMP_API_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    total = data.get("total_count", 0)
    results = data.get("results", [])

    notices = []
    for record in results:
        try:
            # v2.1 API: fields are at top level, not nested
            if "fields" not in record:
                record = {"fields": record, "recordid": record.get("idweb", "")}
            notices.append(normalize_boamp_record(record))
        except Exception:
            continue

    return total, notices


async def get_boamp_notice(notice_id: str) -> Optional[NoticeModel]:
    """Fetch a single BOAMP notice by ID."""
    params = {
        "where": f'idweb="{notice_id}"',
        "limit": 1,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(BOAMP_API_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    results = data.get("results", [])
    if not results:
        return None

    record = results[0]
    if "fields" not in record:
        record = {"fields": record, "recordid": record.get("idweb", "")}
    return normalize_boamp_record(record)
