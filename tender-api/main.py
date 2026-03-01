"""
Tender Intelligence API
=======================
Automated public procurement analysis for France (BOAMP) and Europe (TED).

Version: 1.0.0
Author: TenderBot
"""
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

from routers import search, sectors, notices
from models.notice import APIStatus

# ── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Tender Intelligence API",
    description="""
## Tender Intelligence API

Real-time access to **French (BOAMP)** and **European (TED)** public procurement notices,
with structured extraction of key fields:

- 📋 **Title & Description** — what the contracting authority needs
- 💶 **Budget** — estimated contract value in EUR
- ⏰ **Deadline** — response deadline + days remaining
- 🏭 **Sector** — derived from CPV codes (IT, Construction, Health, etc.)
- 🏛️ **Buyer** — contracting authority name & location
- 📌 **CPV Codes** — standard European procurement classification

### Data Sources
| Source | Coverage | Update Frequency |
|--------|----------|-----------------|
| **BOAMP** | France national | 2× / day |
| **TED** | All EU Member States | Daily |

### Authentication
Include your RapidAPI key in the `X-RapidAPI-Key` header.

### Rate Limits
- **Free** plan: 100 requests/month
- **Basic** plan: 1,000 requests/month @ €29/month
- **Pro** plan: 10,000 requests/month @ €99/month
- **Enterprise**: Unlimited @ €299/month
""",
    version="1.0.0",
    contact={
        "name": "Tender Intelligence Support",
        "url": "https://rapidapi.com/",
    },
    license_info={
        "name": "MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(search.router)
app.include_router(sectors.router)
app.include_router(notices.router)

# ── Root Endpoint ─────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": "Tender Intelligence API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "search": "GET /search?q={keyword}&source={boamp|ted|all}",
            "sectors": "GET /sectors/{sector_id}",
            "sectors_list": "GET /sectors",
            "cpv": "GET /sectors/cpv/{cpv_prefix}",
            "notice_detail": "GET /notices/{source}/{notice_id}",
            "health": "GET /health",
        },
    }


@app.get(
    "/health",
    response_model=APIStatus,
    tags=["System"],
    summary="API health check",
    description="Returns the current status of the API and upstream data sources.",
)
async def health_check():
    sources_status = {}

    # Check BOAMP
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records",
                params={"limit": 1},
            )
            sources_status["boamp"] = "ok" if r.status_code == 200 else f"error_{r.status_code}"
    except Exception:
        sources_status["boamp"] = "unreachable"

    # Check TED
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                "https://api.ted.europa.eu/v3/notices/search",
                json={"query": "*", "page": 1, "limit": 1},
            )
            sources_status["ted"] = "ok" if r.status_code == 200 else f"error_{r.status_code}"
    except Exception:
        sources_status["ted"] = "unreachable"

    overall = "ok" if all(v == "ok" for v in sources_status.values()) else "degraded"

    return APIStatus(
        status=overall,
        version="1.0.0",
        sources=sources_status,
    )


# ── Error Handlers ────────────────────────────────────────────────────────────

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "not_found", "message": str(exc.detail), "docs": "/docs"},
    )


@app.exception_handler(422)
async def validation_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "detail": exc.errors(), "docs": "/docs"},
    )
