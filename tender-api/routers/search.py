"""
Keyword search endpoint — searches BOAMP and/or TED.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Literal
import asyncio

from models.notice import SearchResult
from services.boamp import search_boamp
from services.ted import search_ted

router = APIRouter(prefix="/search", tags=["Search"])


@router.get(
    "",
    response_model=SearchResult,
    summary="Search procurement notices by keyword",
    description="""
Search across French (BOAMP) and/or European (TED) public procurement notices
using keywords. Results are sorted by publication date (newest first).

**Example queries:**
- `?q=informatique&source=boamp` → IT contracts in France
- `?q=consulting&source=ted&country=FR` → Consulting in Europe
- `?q=travaux+batiment&source=all` → Construction work, all sources
""",
)
async def search_notices(
    q: str = Query(..., min_length=2, max_length=200, description="Search keyword(s)"),
    source: Literal["boamp", "ted", "all"] = Query(
        default="all", description="Data source: boamp (France), ted (Europe), or all"
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=50, description="Results per page"),
    only_active: bool = Query(default=True, description="Only return notices with future deadlines"),
    country: Optional[str] = Query(
        default=None, max_length=2, description="Filter TED results by country code (e.g. FR, DE, ES)"
    ),
):
    offset = (page - 1) * per_page

    try:
        if source == "boamp":
            total, notices = await search_boamp(
                query=q, limit=per_page, offset=offset, only_active=only_active
            )
        elif source == "ted":
            total, notices = await search_ted(
                query=q, limit=per_page, page=page, only_active=only_active, country=country
            )
        else:
            # Query both in parallel
            boamp_task = search_boamp(query=q, limit=per_page // 2, offset=0, only_active=only_active)
            ted_task = search_ted(query=q, limit=per_page // 2, page=1, only_active=only_active, country=country)

            (boamp_total, boamp_notices), (ted_total, ted_notices) = await asyncio.gather(
                boamp_task, ted_task, return_exceptions=False
            )
            notices = boamp_notices + ted_notices
            total = boamp_total + ted_total

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream API error: {str(e)}")

    return SearchResult(
        total=total,
        page=page,
        per_page=per_page,
        source=source,
        notices=notices,
    )
