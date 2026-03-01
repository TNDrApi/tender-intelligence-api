""
TED (Tenders Electronic Daily) API client - European public procurement.
Uses the official TED API v3 - free, no API key required for search.
Base URL: https://api.ted.europa.eu/v3

Official docs: https://docs.ted.europa.eu/api/latest/index.html
"""
import httpx
import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from models.notice import NoticeModel, BuyerModel
from services.boamp import cpv_to_sector, days_until

TED_API_BASE = "https://api.ted.europa.eu/v3/notices/search"
TED_NOTICE_URL = "https://ted.europa.eu/en/notice/{id}"

# TED notice type mapping
TED_TYPE_MAP = {
        "CN": "Avis de marché",
        "CAN": "Avis d'attribution",
        "PIN": "Avis de préinformation",
        "QSN": "Système de qualification",
        "DP": "Avis de conception",
        "PD": "Document de passation de marchés",
}

# TED procedure type mapping
TED_PROCEDURE_MAP = {
        "1": "Ouverte",
        "2": "Restreinte",
        "3": "Négociée avec publication",
        "4": "Dialogue compétitif",
        "5": "Négociée sans publication",
        "6": "Conception",
        "8": "Partenariat d'innovation",
}


def parse_ted_date(val: Any) -> Optional[str]:
        """Parse TED date fields into ISO string."""
        if not val:
                    return None
                if isinstance(val, str):
                            for fmt in ("%Y%m%d", "%Y-%m-%d", "%d/%m/%Y"):
                                            try:
                                                                return datetime.strptime(val[:10], fmt[:len(val[:10])]).date().isoformat()
                                            except ValueError:
                                                                continue
                                                        return val[:10] if len(val) >= 10 else val
                                    return None


def extract_ted_budget(notice: Dict[str, Any]) -> tuple[Optional[float], Optional[float], Optional[str]]:
        """Extract budget from TED notice structure."""
    for path in [
                ["estimatedValueInfo", "value"],
                ["totalValue", "value"],
                ["awardedContract", "values", 0, "value"],
    ]:
                val = notice
        try:
                        for key in path:
                                            val = val[key]
                                        amount = float(val)
            return amount, amount, f"{amount:,.0f} €".replace(",", " ")
except (KeyError, IndexError, TypeError, ValueError):
            continue
    return None, None, None


def normalize_ted_record(notice: Dict[str, Any]) -> NoticeModel:
        """Convert a raw TED API v3 notice into a normalized NoticeModel."""

    # ID
    notice_id = notice.get("noticeId") or notice.get("id") or ""
    publication_number = notice.get("publicationNumber") or notice_id
    url = TED_NOTICE_URL.format(id=publication_number)

    # Title
    title_obj = notice.get("title") or {}
    if isinstance(title_obj, dict):
                title = (
                                title_obj.get("fra")
                                or title_obj.get("fre")
                                or title_obj.get("eng")
                                or next(iter(title_obj.values()), "Sans titre")
                )
elif isinstance(title_obj, str):
        title = title_obj
else:
        title = notice.get("shortDescription", {}).get("fra") or "Sans titre"

    # Buyer
    buyer_obj = (notice.get("buyers") or [{}])[0] if notice.get("buyers") else {}
    buyer = BuyerModel(
                name=buyer_obj.get("officialName") or buyer_obj.get("name"),
                city=buyer_obj.get("address", {}).get("city") if isinstance(buyer_obj.get("address"), dict) else None,
                country=buyer_obj.get("address", {}).get("country", {}).get("code", "EU")
                if isinstance(buyer_obj.get("address"), dict)
                else "EU",
    )

    # Dates
    pub_date = parse_ted_date(notice.get("publicationDate") or notice.get("dispatchDate"))
    deadline_raw = (
                notice.get("submissionDeadlineDate")
                or notice.get("deadlineForSubmission")
                or notice.get("tenderingDeadline")
    )
    deadline = parse_ted_date(deadline_raw)

    # Budget
    bmin, bmax, bdisplay = extract_ted_budget(notice)

    # CPV
    cpv_list = notice.get("classificationCodes") or notice.get("cpvCodes") or []
    if isinstance(cpv_list, list):
                cpv_codes = [str(c).split("-")[0].strip() for c in cpv_list if c]
else:
        cpv_codes = []

    cpv_labels = [cpv_to_sector(c) for c in cpv_codes]
    sector = cpv_labels[0] if cpv_labels else "Non classifié"

    # Type & procedure
    notice_type_code = notice.get("noticeType") or ""
    notice_type = TED_TYPE_MAP.get(notice_type_code, notice_type_code)

    procedure_code = str(notice.get("procedureType") or "")
    procedure_type = TED_PROCEDURE_MAP.get(procedure_code, procedure_code)

    # Description
    desc_obj = notice.get("description") or notice.get("shortDescription") or {}
    if isinstance(desc_obj, dict):
                description = desc_obj.get("fra") or desc_obj.get("fre") or desc_obj.get("eng") or None
elif isinstance(desc_obj, str):
        description = desc_obj
else:
        description = None

    # Duration
    duration_months = None
    dur = notice.get("contractDuration") or {}
    if isinstance(dur, dict):
                try:
                                duration_months = int(dur.get("durationInMonths") or dur.get("months") or 0) or None
                except (ValueError, TypeError):
            pass

    # Keywords from title
    stop_words = {"of", "the", "and", "for", "with", "in", "to", "de", "du", "des", "le", "la", "les"}
    words = re.findall(r"\b[a-zA-Z-é]{4,}\b", title.lower())
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
                notice_type=notice_type,
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
        limit: int = 20,
        page: int = 1,
        only_active: bool = True,
        country: Optional[str] = None,
) -> tuple[int, List[NoticeModel]]:
        """
            Search TED notices using the v3 Search API.
                Returns (total_count, list_of_normalized_notices).
                    """

    # Build filters list (TED v3 uses simple text query + separate filters)
    filters = {}

    if only_active:
                today = date.today().strftime("%Y%m%d")
        filters["deadlineForSubmission"] = {"gte": today}

    if country:
                filters["buyers.address.country.code"] = country.upper()

    if cpv_prefix:
                filters["classificationCodes"] = {"startsWith": cpv_prefix}

    payload = {
                "query": query or "",
                "page": page,
                "limit": min(limit, 100),
                "filters": filters,
                "fields": [
                                "noticeId", "publicationNumber", "noticeType", "publicationDate",
                                "title", "description", "shortDescription", "buyers",
                                "classificationCodes", "cpvCodes", "submissionDeadlineDate",
                                "deadlineForSubmission", "estimatedValueInfo", "totalValue",
                                "procedureType", "contractDuration", "dispatchDate"
                ],
                "scope": "ALL",
                "language": "FRA",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(TED_API_BASE, json=payload)
        resp.raise_for_status()
        data = resp.json()

    total = data.get("total", 0) or data.get("totalElements", 0)
    notices_raw = data.get("notices", []) or data.get("content", [])

    notices = []
    for raw in notices_raw:
                try:
                                notices.append(normalize_ted_record(raw))
                except Exception:
            continue

    return total, notices


async def get_ted_notice(notice_id: str) -> Optional[NoticeModel]:
        """Fetch a single TED notice by its publication number."""
    url = f"https://api.ted.europa.eu/v3/notices/{notice_id}"
    async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url)
        if resp.status_code == 404:
                        return None
        resp.raise_for_status()
        data = resp.json()
    return normalize_ted_record(data)
TED_API_BASE = "https://api.ted.europa.eu/v3/notices/search"
TED_NOTICE_URL = "https://ted.europa.eu/en/notice/{id}"

# TED notice type mapping
TED_TYPE_MAP = {
    "CN": "Avis de marché",
    "CAN": "Avis d'attribution",
    "PIN": "Avis de préinformation",
    "QSN": "Système de qualification",
    "DP": "Avis de conception",
    "PD": "Document de passation de marchés",
}

# TED procedure type mapping
TED_PROCEDURE_MAP = {
    "1": "Ouverte",
    "2": "Restreinte",
    "3": "Négociée avec publication",
    "4": "Dialogue compétitif",
    "5": "Négociée sans publication",
    "6": "Conception",
    "8": "Partenariat d'innovation",
}


def parse_ted_date(val: Any) -> Optional[str]:
    """Parse TED date fields into ISO string."""
    if not val:
        return None
    if isinstance(val, str):
        # Try various formats
        for fmt in ("%Y%m%d", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(val[:10], fmt[:len(val[:10])]).date().isoformat()
            except ValueError:
                continue
        return val[:10] if len(val) >= 10 else val
    return None


def extract_ted_budget(notice: Dict[str, Any]) -> tuple[Optional[float], Optional[float], Optional[str]]:
    """Extract budget from TED notice structure."""
    # TED uses various value fields
    for path in [
        ["estimatedValueInfo", "value"],
        ["totalValue", "value"],
        ["awardedContract", "values", 0, "value"],
    ]:
        val = notice
        try:
            for key in path:
                val = val[key]
            amount = float(val)
            return amount, amount, f"{amount:,.0f} €".replace(",", " ")
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    return None, None, None


def normalize_ted_record(notice: Dict[str, Any]) -> NoticeModel:
    """Convert a raw TED API v3 notice into a normalized NoticeModel."""

    # ID
    notice_id = notice.get("noticeId") or notice.get("id") or ""
    publication_number = notice.get("publicationNumber") or notice_id
    url = TED_NOTICE_URL.format(id=publication_number)

    # Title — TED stores multilingual, prefer FR then EN
    title_obj = notice.get("title") or {}
    if isinstance(title_obj, dict):
        title = (
            title_obj.get("fra")
            or title_obj.get("fre")
            or title_obj.get("eng")
            or next(iter(title_obj.values()), "Sans titre")
        )
    elif isinstance(title_obj, str):
        title = title_obj
    else:
        title = notice.get("shortDescription", {}).get("fra") or "Sans titre"

    # Buyer
    buyer_obj = (notice.get("buyers") or [{}])[0] if notice.get("buyers") else {}
    buyer = BuyerModel(
        name=buyer_obj.get("officialName") or buyer_obj.get("name"),
        city=buyer_obj.get("address", {}).get("city") if isinstance(buyer_obj.get("address"), dict) else None,
        country=buyer_obj.get("address", {}).get("country", {}).get("code", "EU")
        if isinstance(buyer_obj.get("address"), dict)
        else "EU",
    )

    # Dates
    pub_date = parse_ted_date(notice.get("publicationDate") or notice.get("dispatchDate"))
    deadline_raw = (
        notice.get("submissionDeadlineDate")
        or notice.get("deadlineForSubmission")
        or notice.get("tenderingDeadline")
    )
    deadline = parse_ted_date(deadline_raw)

    # Budget
    bmin, bmax, bdisplay = extract_ted_budget(notice)

    # CPV
    cpv_list = notice.get("classificationCodes") or notice.get("cpvCodes") or []
    if isinstance(cpv_list, list):
        cpv_codes = [str(c).split("-")[0].strip() for c in cpv_list if c]
    else:
        cpv_codes = []

    cpv_labels = [cpv_to_sector(c) for c in cpv_codes]
    sector = cpv_labels[0] if cpv_labels else "Non classifié"

    # Type & procedure
    notice_type_code = notice.get("noticeType") or ""
    notice_type = TED_TYPE_MAP.get(notice_type_code, notice_type_code)

    procedure_code = str(notice.get("procedureType") or "")
    procedure_type = TED_PROCEDURE_MAP.get(procedure_code, procedure_code)

    # Description
    desc_obj = notice.get("description") or notice.get("shortDescription") or {}
    if isinstance(desc_obj, dict):
        description = desc_obj.get("fra") or desc_obj.get("fre") or desc_obj.get("eng") or None
    elif isinstance(desc_obj, str):
        description = desc_obj
    else:
        description = None

    # Duration
    duration_months = None
    dur = notice.get("contractDuration") or {}
    if isinstance(dur, dict):
        try:
            duration_months = int(dur.get("durationInMonths") or dur.get("months") or 0) or None
        except (ValueError, TypeError):
            pass

    # Keywords from title
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
        notice_type=notice_type,
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
    limit: int = 20,
    page: int = 1,
    only_active: bool = True,
    country: Optional[str] = None,
) -> tuple[int, List[NoticeModel]]:
    """
    Search TED notices using the v3 Search API.
    Returns (total_count, list_of_normalized_notices).
    """
    # Build expert query
    query_parts = []

    if query:
        query_parts.append(f'TD ~ "{query}"')  # TD = Title/Description

    if cpv_prefix:
        query_parts.append(f'PC = {cpv_prefix}*')  # PC = CPV code

    if only_active:
        today = date.today().strftime("%Y%m%d")
        query_parts.append(f'RD >= {today}')  # RD = receipt deadline

    if country:
        query_parts.append(f'CY = {country.upper()}')

    # Default to recent contract notices if no filter
    if not query_parts:
        query_parts.append("ND = CN*")  # CN = Contract Notice

    expert_query = " AND ".join(query_parts) if query_parts else "*"

    payload = {
        "query": expert_query,
        "page": page,
        "limit": min(limit, 100),
        "fields": [
            "noticeId", "publicationNumber", "noticeType", "publicationDate",
            "title", "description", "shortDescription", "buyers",
            "classificationCodes", "cpvCodes", "submissionDeadlineDate",
            "deadlineForSubmission", "estimatedValueInfo", "totalValue",
            "procedureType", "contractDuration", "dispatchDate"
        ],
        "scope": "ALL",
        "language": "FRA",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(TED_API_BASE, json=payload)
        resp.raise_for_status()
        data = resp.json()

    total = data.get("total", 0) or data.get("totalElements", 0)
    notices_raw = data.get("notices", []) or data.get("content", [])

    notices = []
    for raw in notices_raw:
        try:
            notices.append(normalize_ted_record(raw))
        except Exception:
            continue

    return total, notices


async def get_ted_notice(notice_id: str) -> Optional[NoticeModel]:
    """Fetch a single TED notice by publication number."""
    payload = {
        "query": f'ND = {notice_id}',
        "page": 1,
        "limit": 1,
        "scope": "ALL",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(TED_API_BASE, json=payload)
        resp.raise_for_status()
        data = resp.json()

    notices_raw = data.get("notices", []) or data.get("content", [])
    if not notices_raw:
        return None
    return normalize_ted_record(notices_raw[0])
