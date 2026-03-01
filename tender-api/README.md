# Tender Intelligence API

**Automated public procurement analysis for France (BOAMP) and Europe (TED).**

Real-time structured extraction of key fields from public tender notices — no scraping,
no authentication headaches. Powered by official open-data APIs.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/tender-intelligence-api
cd tender-intelligence-api

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run locally
uvicorn main:app --reload --port 8000
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API docs.

---

## API Endpoints

### 1. `GET /search` — Keyword Search

Search notices by keyword across BOAMP and/or TED.

```
GET /search?q=logiciels&source=boamp&per_page=10
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | **required** | Search keyword(s) |
| `source` | enum | `all` | `boamp`, `ted`, or `all` |
| `page` | int | `1` | Page number |
| `per_page` | int | `20` | Results per page (max 50) |
| `only_active` | bool | `true` | Only future deadlines |
| `country` | string | — | Filter TED by country (e.g. `FR`) |

**Example response:**
```json
{
  "total": 142,
  "page": 1,
  "per_page": 10,
  "source": "boamp",
  "notices": [
    {
      "id": "boamp-2024-123456",
      "source": "boamp",
      "title": "Maintenance de logiciels de gestion RH",
      "buyer": { "name": "Mairie de Lyon", "city": "Lyon", "country": "FR" },
      "publication_date": "2024-09-01",
      "deadline": "2024-10-15",
      "deadline_days_remaining": 44,
      "budget_display": "120 000 €",
      "cpv_codes": ["48400000"],
      "sector": "Informatique & Logiciels",
      "notice_type": "Appel d'offres ouvert",
      "url": "https://www.boamp.fr/avis/detail/2024-123456"
    }
  ]
}
```

---

### 2. `GET /sectors` — List Sectors

Returns all available sector IDs you can filter by.

```
GET /sectors
```

**Available sectors:** `it`, `construction`, `sante`, `transport`, `energie`,
`telecom`, `formation`, `ingenierie`, `securite`, `environnement`, `services`,
`alimentaire`, `rd`, `mobilier`, `immobilier`

---

### 3. `GET /sectors/{sector_id}` — Browse by Sector

Retrieve notices for a specific sector.

```
GET /sectors/it?source=all&per_page=20
GET /sectors/construction?source=boamp&only_active=true
```

---

### 4. `GET /sectors/cpv/{cpv_prefix}` — Filter by CPV Code

```
GET /sectors/cpv/72       → All IT services
GET /sectors/cpv/4512     → Specific construction works
GET /sectors/cpv/48000000 → Exact CPV code match
```

---

### 5. `GET /notices/{source}/{id}` — Notice Detail

Retrieve the full structured details of a specific notice.

```
GET /notices/boamp/2024-123456
GET /notices/ted/2024-S-200-123456
```

---

### 6. `GET /health` — Health Check

Returns API status and upstream source availability.

---

## Data Model

Every notice returns these fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique ID (`boamp-XXXX` or `ted-XXXX`) |
| `source` | string | `boamp` or `ted` |
| `title` | string | Notice object / title |
| `buyer.name` | string | Contracting authority name |
| `buyer.city` | string | City |
| `buyer.country` | string | Country code (ISO 2) |
| `publication_date` | ISO date | When it was published |
| `deadline` | ISO date | Submission deadline |
| `deadline_days_remaining` | int | Days until deadline |
| `budget_display` | string | Human-readable budget (`"120 000 €"`) |
| `budget_min` | float | Min budget in EUR |
| `budget_max` | float | Max budget in EUR |
| `cpv_codes` | string[] | CPV classification codes |
| `sector` | string | Human-readable sector label |
| `notice_type` | string | Type of notice |
| `procedure_type` | string | Procurement procedure |
| `description` | string | Detailed description |
| `url` | string | Link to original notice |
| `keywords` | string[] | Extracted keywords |
| `duration_months` | int | Contract duration in months |

---

## Data Sources

### BOAMP (France)
- Official API: [boamp-datadila.opendatasoft.com](https://boamp-datadila.opendatasoft.com)
- No API key required
- Updated 2× per day, 7 days/week
- Coverage: all French public procurement above €40,000

### TED (Europe)
- Official API: [api.ted.europa.eu/v3](https://docs.ted.europa.eu/api/latest/index.html)
- No API key required for search
- Coverage: all EU member states, updated daily
- Data from 27 EU countries + EEA

---

## Deployment

### Railway (Recommended)

1. Push code to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select the repo — Railway auto-detects Python and deploys
4. Note the public URL (e.g. `https://tender-api.railway.app`)

### Render

1. Push code to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect repo — Render reads `render.yaml` automatically
4. Free plan gives 512MB RAM, spins down after 15min inactivity

---

## RapidAPI Integration

After deployment, connect your live URL to RapidAPI:

1. Create API at [rapidapi.com/provider](https://rapidapi.com/provider)
2. Set Base URL to your Railway/Render URL
3. Configure pricing tiers (see `RAPIDAPI_PRODUCT.md`)
4. Submit for review

---

## License

MIT — free to use, modify, and redistribute.
