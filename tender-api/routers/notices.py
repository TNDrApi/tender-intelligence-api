"""
Notice detail endpoint — fetch full details for a specific notice.
"""
from fastapi import APIRouter, Path, HTTPException
from typing import Literal

from models.notice import NoticeModel
from services.boamp import get_boamp_notice
from services.ted import get_ted_notice

router = APIRouter(prefix="/notices", tags=["Notices"])


@router.get(
    "/{source}/{notice_id}",
    response_model=NoticeModel,
    summary="Get notice details",
    description="""
Retrieve the full details of a specific procurement notice.

**Source options:**
- `boamp` — French national notices
- `ted` — European notices

**ID format:**
- For BOAMP: use the `idweb` value (e.g. `2024-123456`)
- For TED: use the publication number (e.g. `2024/S 123-456789`)

**Tip:** IDs are returned in the `id` field of search results (strip the `boamp-` or `ted-` prefix).
""",
)
async def get_notice(
    source: Literal["boamp", "ted"] = Path(..., description="Source: 'boamp' or 'ted'"),
    notice_id: str = Path(..., min_length=1, max_length=100, description="Notice ID"),
):
    try:
        if source == "boamp":
            notice = await get_boamp_notice(notice_id)
        else:
            notice = await get_ted_notice(notice_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream API error: {str(e)}")

    if not notice:
        raise HTTPException(status_code=404, detail=f"Notice '{notice_id}' not found in {source}.")

    return notice
