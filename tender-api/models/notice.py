"""
Pydantic models for normalized procurement notices.
Supports both BOAMP (France) and TED (Europe) sources.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class BuyerModel(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = Field(default="FR")


class NoticeModel(BaseModel):
    """Unified procurement notice model normalized from BOAMP or TED."""

    id: str = Field(..., description="Unique identifier")
    source: str = Field(..., description="Data source: 'boamp' or 'ted'")
    title: str = Field(..., description="Notice title / object")
    buyer: Optional[BuyerModel] = Field(default=None, description="Contracting authority")

    publication_date: Optional[str] = Field(default=None, description="Publication date (ISO 8601)")
    deadline: Optional[str] = Field(default=None, description="Response deadline (ISO 8601)")
    deadline_days_remaining: Optional[int] = Field(default=None, description="Days until deadline")

    budget_min: Optional[float] = Field(default=None, description="Minimum estimated budget (EUR)")
    budget_max: Optional[float] = Field(default=None, description="Maximum estimated budget (EUR)")
    budget_display: Optional[str] = Field(default=None, description="Human-readable budget string")

    cpv_codes: List[str] = Field(default_factory=list, description="CPV codes (procurement categories)")
    cpv_labels: List[str] = Field(default_factory=list, description="CPV labels in French/English")
    sector: Optional[str] = Field(default=None, description="Sector derived from CPV")

    notice_type: Optional[str] = Field(default=None, description="Type: appel_offres, marche_adapte, concession...")
    procedure_type: Optional[str] = Field(default=None, description="Procedure: ouverte, restreinte, negociee...")

    description: Optional[str] = Field(default=None, description="Full description / lot details")
    url: Optional[str] = Field(default=None, description="Original notice URL")

    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")
    required_profile: Optional[str] = Field(default=None, description="Required contractor profile / criteria")
    duration_months: Optional[int] = Field(default=None, description="Contract duration in months")

    raw_data: Optional[dict] = Field(default=None, description="Original raw data from source", exclude=True)


class SearchResult(BaseModel):
    total: int = Field(..., description="Total matching notices")
    page: int = Field(default=1)
    per_page: int = Field(default=20)
    source: str = Field(default="all", description="Source queried: boamp, ted, or all")
    notices: List[NoticeModel]


class SectorStats(BaseModel):
    sector: str
    cpv_prefix: str
    count: int
    latest_notice_date: Optional[str] = None


class APIStatus(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    sources: dict
    total_notices_today: Optional[int] = None
