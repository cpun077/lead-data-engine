# CLAUDE.md

## Response style
- Keep responses concise; avoid exceeding ~500 output tokens unless long-form is explicitly requested.
- Prefer bullet summaries over prose walls.

## Project
Company lists + their GTM/revenue contacts, stored as per-industry CSVs.

- `data/companies/<industry>.csv` — `category, rank, company, domain, contact_count`
- `data/contacts/<industry>.csv` — `company, name, title` (linked by exact `company` name)
- `data/contacts/*` is git-ignored.

## Key rules
- `company` is the exact-string key for routing, dedup `(company, name)`, and `contact_count`. It MUST match `companies.company` verbatim.
- `contact_count` is derived — keep it in sync via `recount_contacts.update_counts(only=…)`.

## Scripts (run with venv: `source .venv/bin/activate`)
- `scripts/parse_linkedin.py` — parse a raw Sales Nav paste → dedup-append → recount. Manual fallback flow.
- `scripts/recount_contacts.py` — refresh `contact_count` (all, or scoped via `update_counts(only=…)`).
- `scripts/serve.py` — local receiver (127.0.0.1:8765) for the Chrome extension.
- `extension/` — MV3 extension that grabs a Sales Nav page and POSTs to serve.py. See `extension/README.md`.
