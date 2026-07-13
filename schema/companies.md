# Companies schema

One row per company. Files live in `data/companies/`, split by industry list.
The full combined source is preserved at `data/raw/companies_master.csv`.

**Primary key:** `domain` (unique, stable — use this for all joins, never `company`).

| Column          | Description                                                        |
|-----------------|--------------------------------------------------------------------|
| `category`      | Industry list the company belongs to (e.g. "AmLaw 100 law firms"). |
| `rank`          | Rank within that list.                                             |
| `company`       | Display name (may contain commas / parentheticals).               |
| `domain`        | Primary web domain. **Join key.**                                 |
| `contact_count` | Number of contacts recorded for this company in `data/contacts/`. |

## Files

| File                     | List                                          |
|--------------------------|-----------------------------------------------|
| `accounting.csv`         | Accounting Today Top 100 accounting firms     |
| `amlaw.csv`              | AmLaw 100 law firms                           |
| `business_insurance.csv` | Business Insurance Top 100 insurance brokers  |
| `consulting_tier1.csv`   | Tier 1 strategy consulting firms              |
| `consulting_tier2.csv`   | Tier 2 strategy consulting firms              |
| `govt_relations.csv`     | Top 50 government relations firms             |
