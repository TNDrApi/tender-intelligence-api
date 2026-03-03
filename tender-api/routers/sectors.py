"""
Sector/CPV-based search endpoint.
Lets users browse notices by procurement sector (derived from CPV codes).
"""
from fastapi import APIRouter, Query, HTTPException, Path
from typing import Optional, Literal, List
import asyncio

from models.notice import SearchResult, SectorStats
from services.boamp import search_boamp, CPV_SECTOR_MAP
from services.ted import search_ted

router = APIRouter(prefix="/sectors", tags=["Sectors"])


# Human-readable sector list with their CPV prefixes
AVAILABLE_SECTORS = [
    {"id": "it", "label": "Informatique & Logiciels", "cpv_prefixes": ["30", "48", "72"]},
    {"id": "construction", "label": "Travaux de Construction", "cpv_prefixes": ["44", "45"]},
    {"id": "sante", "label": "Santé & Médical", "cpv_prefixes": ["33", "85"]},
    {"id": "transport", "label": "Transport & Logistique", "cpv_prefixes": ["34", "60", "63"]},
    {"id": "energie", "label": "Energie & Utilities", "cpv_prefixes": ["09", "65"]},
    {"id": "telecom", "label": "Télécommunications", "cpv_prefixes": ["32", "64"]},
    {"id": "formation", "label": "Formation & Education", "cpv_prefixes": ["80"]},
    {"id": "ingenierie", "label": "Architecture & Ingénierie", "cpv_prefixes": ["71"]},
    {"id": "securite", "label": "Sécurité & Défense", "cpv_prefixes": ["35"]},
    {"id": "environnement", "label": "Environnement & Déchets", "cpv_prefixes": ["77", "90"]},
    {"id": "services", "label": "Services aux Entreprises", "cpv_prefixes": ["79"]},
    {"id": "alimentaire", "label": "Alimentaire & Restauration", "cpv_prefixes": ["15", "55"]},
    {"id": "rd", "label": "R&D & Innovation", "cpv_prefixes": ["73"]},
    {"id": "mobilier", "label": "Mobilier & Equipements", "cpv_prefixes": ["39"]},
    {"id": "immobilier", "label": "Immobilier", "cpv_prefixes": ["70"]},
]

SECTOR_ID_MAP = {s["id"]: s for s in AVAILABLE_SECTORS}


@router.get(
    "",
    summary="List all available sectors",
    description="Returns the list of procurement sectors you can filter by.",
)
async def list_sectors():
    return {
        "sectors": [
            {
                "id": s["id"],
                "label": s["label"],
                "cpv_prefixes": s["cpv_prefixes"],
            }
            for s in AVAILABLE_SECTORS
        ]
    }


@router.get(
    "/{sector_id}",
    response_model=SearchResult,
    summary="Search notices by sector",
    description="""
Retrieve procurement notices filtered by sector (based on CPV codes).

**Available sector IDs:**
it, construction, sante, transport, energie, telecom, formation,
ingenierie, securite, environnement, services, alimentaire, rd, mobilier, immobilier

**Example:** `/sectors/it?source=boamp&per_page=10`
""",
)
async def search_by_sector(
    sector_id: str = Path(..., description="Sector ID (e.g. 'it', 'construction', 'sante')"),
    source: Literal["boamp", "ted", "all"] = Query(default="all"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=50),
    only_active: bool = Query(default=True),
    country: Optional[str] = Query(default=None),
):
    sector_info = SECTOR_ID_MAP.get(sector_id)
    if not sector_info:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown sector '{sector_id}'. Use GET /sectors to list available sectors.",
        )

    cpv_prefixes = sector_info["cpv_prefixes"]
    offset = (page - 1) * per_page

    # BOAMP: utilise le premier préfixe CPV (filtre dc like)
    # TED: passe tous les préfixes pour un filtre OR sur classification-cpv
    primary_cpv = cpv_prefixes[0]

    try:
        if source == "boamp":
            total, notices = await search_boamp(
                cpv_prefix=primary_cpv, limit=per_page, offset=offset, only_active=only_active
            )
        elif source == "ted":
            total, notices = await search_ted(
                cpv_prefixes=cpv_prefixes, limit=per_page, page=page, only_active=only_active, country=country
            )
        else:
            half = per_page // 2
            boamp_task = search_boamp(cpv_prefix=primary_cpv, limit=half, offset=0, only_active=only_active)
            ted_task = search_ted(
                cpv_prefixes=cpv_prefixes, limit=half, page=1, only_active=only_active, country=country
            )
            (bt, bn), (tt, tn) = await asyncio.gather(boamp_task, ted_task)
            notices = bn + tn
            total = bt + tt

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream API error: {str(e)}")

    return SearchResult(
        total=total,
        page=page,
        per_page=per_page,
        source=source,
        notices=notices,
    )


@router.get(
    "/cpv/{cpv_prefix}",
    response_model=SearchResult,
    summary="Search notices by CPV code prefix",
    description="""
Filter notices directly by CPV code prefix (2 to 8 digits).

**Examples:**
- `/sectors/cpv/72` → All IT services (72xxxxxx)
- `/sectors/cpv/4512` → Specific construction works
- `/sectors/cpv/48000000` → Exact CPV match
""",
)
async def search_by_cpv(
    cpv_prefix: str = Path(..., min_length=2, max_length=8, description="CPV code prefix"),
    source: Literal["boamp", "ted", "all"] = Query(default="all"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=50),
    only_active: bool = Query(default=True),
):
    offset = (page - 1) * per_page

    try:
        if source == "boamp":
            total, notices = await search_boamp(
                cpv_prefix=cpv_prefix, limit=per_page, offset=offset, only_active=only_active
            )
        elif source == "ted":
            total, notices = await search_ted(
                cpv_prefix=cpv_prefix, limit=per_page, page=page, only_active=only_active
            )
        else:
            half = per_page // 2
            (bt, bn), (tt, tn) = await asyncio.gather(
                search_boamp(cpv_prefix=cpv_prefix, limit=half, offset=0, only_active=only_active),
                search_ted(cpv_prefix=cpv_prefix, limit=half, page=1, only_active=only_active),
            )
            notices = bn + tn
            total = bt + tt

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream API error: {str(e)}")

    return SearchResult(
        total=total,
        page=page,
        per_page=per_page,
        source=source,
        notices=notices,
    )
