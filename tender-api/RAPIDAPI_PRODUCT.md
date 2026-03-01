# RapidAPI Product Sheet — Tender Intelligence API

## API Name
**Tender Intelligence API — France & Europe**

## Tagline (160 chars max)
> Search, filter, and extract structured data from 50,000+ public procurement notices per year — BOAMP (France) + TED (EU).

## Short Description (for listings)
Real-time access to French and European public tender notices with automatic extraction of key fields: title, buyer, budget, deadline, sector (CPV), and procedure type. Covers BOAMP (France national) and TED (27 EU countries). No scraping required — powered by official open-data APIs.

## Long Description

### What it does
The Tender Intelligence API gives you instant, structured access to public procurement notices from:

- **BOAMP** — France's official procurement bulletin (Bulletin Officiel des Annonces des Marchés Publics). Updated twice daily, covers all contracts above €40,000.
- **TED** — Tenders Electronic Daily, the European Union's official public procurement journal. Covers all 27 EU member states, updated daily.

Instead of parsing complex XML or scraping HTML, you get clean JSON with the fields that matter:

| Field | Example |
|-------|---------|
| Title | "Maintenance logiciels de gestion RH" |
| Buyer | Mairie de Lyon |
| Deadline | 2024-10-15 (44 days remaining) |
| Budget | 120 000 € |
| Sector | Informatique & Logiciels |
| CPV codes | 48400000, 72500000 |
| Notice type | Appel d'offres ouvert |
| Source URL | boamp.fr/avis/detail/... |

### Use cases

- **Business intelligence** — Monitor contracts in your sector before competitors
- **CRM enrichment** — Auto-populate lead data with active tenders
- **Alerting systems** — Trigger notifications when relevant tenders are published
- **Market research** — Analyze public spending trends by sector, region, or buyer
- **Competitive analysis** — Track which suppliers win contracts in your market

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /search?q={keyword}` | Keyword search across all sources |
| `GET /sectors/{sector_id}` | Browse by sector (IT, Construction, Health…) |
| `GET /sectors/cpv/{cpv_code}` | Filter by CPV procurement code |
| `GET /notices/{source}/{id}` | Full notice detail |
| `GET /sectors` | List all available sectors |
| `GET /health` | API status check |

### Why use this instead of direct APIs?

| Feature | Raw BOAMP/TED | This API |
|---------|---------------|----------|
| Unified JSON format | ❌ Different schemas | ✅ |
| Budget extraction | ❌ Often buried in text | ✅ |
| Days remaining calculation | ❌ Manual | ✅ Auto |
| Sector labels from CPV | ❌ Just codes | ✅ Human labels |
| Cross-source search | ❌ Two separate APIs | ✅ One call |
| Error handling & timeouts | ❌ Your problem | ✅ Handled |

---

## Pricing Tiers

### FREE
- **100 requests/month**
- All endpoints available
- Rate limit: 10 req/min
- **€0/month**

### BASIC
- **1,000 requests/month**
- All endpoints
- Rate limit: 30 req/min
- Overage: €0.05/request
- **€29/month**

### PRO ⭐ Most Popular
- **10,000 requests/month**
- All endpoints
- Rate limit: 60 req/min
- Overage: €0.02/request
- Priority support
- **€99/month**

### ENTERPRISE
- **Unlimited requests**
- Rate limit: 200 req/min
- Custom SLA
- Dedicated support
- **€299/month**

---

## Category Tags
`Public Procurement` • `Government` • `France` • `Europe` • `BOAMP` • `TED` • `Tenders` • `B2B` • `Business Intelligence` • `Open Data`

## Primary Category
Business Software > Government & Legal

## Supported Countries
🇫🇷 France · 🇩🇪 Germany · 🇪🇸 Spain · 🇮🇹 Italy · 🇧🇪 Belgium · 🇳🇱 Netherlands · 🇵🇱 Poland · 🇸🇪 Sweden · and all 27 EU member states

## Sample Request (for RapidAPI docs)

```bash
curl --request GET \
  --url 'https://tender-intelligence-api.railway.app/search?q=informatique&source=boamp&per_page=5' \
  --header 'X-RapidAPI-Key: YOUR_API_KEY' \
  --header 'X-RapidAPI-Host: tender-intelligence-api.p.rapidapi.com'
```

## Sample Response (for RapidAPI docs)

```json
{
  "total": 89,
  "page": 1,
  "per_page": 5,
  "source": "boamp",
  "notices": [
    {
      "id": "boamp-24-154782",
      "source": "boamp",
      "title": "Maintenance et évolution du système d'information RH",
      "buyer": {
        "name": "Région Auvergne-Rhône-Alpes",
        "city": "Lyon",
        "country": "FR"
      },
      "publication_date": "2024-09-02",
      "deadline": "2024-10-18",
      "deadline_days_remaining": 46,
      "budget_min": 250000.0,
      "budget_max": 250000.0,
      "budget_display": "250 000 €",
      "cpv_codes": ["72500000", "72600000"],
      "cpv_labels": ["Informatique, Services IT", "Informatique, Services IT"],
      "sector": "Informatique, Services IT",
      "notice_type": "Appel d'offres ouvert",
      "procedure_type": "Ouverte",
      "url": "https://www.boamp.fr/avis/detail/24-154782",
      "keywords": ["maintenance", "système", "information", "évolution"],
      "duration_months": 36
    }
  ]
}
```
