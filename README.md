# lead-data-engine

Build and maintain a database of GTM/marketing contacts at target companies across industries. Two collection methods: automated web scraping with AI evaluation, and semi-automated LinkedIn Sales Nav extraction via Chrome extension.

## Layout

```
data/companies/<industry>.csv   — company rosters (category, rank, company, domain, contact_count)
data/contacts/<industry>.csv    — GTM contacts (company, name, title)
data/golden.jsonl               — rubric regression test cases
extension/                      — MV3 Chrome extension (see extension/README.md)
schema/                         — column definitions
scripts/                        — all automation
```

Industries: `accounting`, `amlaw`, `business_insurance`, `consulting_tier1`, `consulting_tier2`, `govt_relations`

Contact-to-company link is by **exact `company` name**. This drives routing, dedup (`company` + `name`), and `contact_count`.

GTM = marketing, BD, communications, PR, events, brand, content, CRM, audience/engagement growth, and revenue leadership above them.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Method 1: Scrape + Evaluate (primary)

Searches DuckDuckGo for LinkedIn profiles matching a target company, then uses Claude to judge each result against a rubric.

### Quick start

First time: `playwright install chromium`

In Claude Code, type `/scrape-leads`. It will ask for the company name and page depth, then runs the full pipeline (query → scrape → merge → evaluate → review unsure). To adjudicate unsure candidates later, type `/review-leads`.

### Scripts

| Script | Purpose |
|--------|---------|
| `query_builder.py` | Generates DuckDuckGo `site:linkedin.com/in` queries with GTM keyword expansion |
| `duckduckgo_search.py` | Scrapes DDG results. `--batch` for file of queries, `--pages N` for depth, `--show` to open browser (fixes challenges) |
| `merge_results.py` | Deduplicates and merges per-query JSON files into one |
| `evaluate_leads.py` | Two-stage filter: fast rules (blocked titles, wrong company) then Claude judge per `rubric.md`. Outputs: accepted → CSV, unsure → `data/review_queue.json` |
| `recount_contacts.py` | Rebuilds `contact_count` in all company CSVs from contact CSVs |

### Evaluate options

```bash
# Check rubric regression against golden set
python scripts/evaluate_leads.py --check

# Apply human decisions from review queue
python scripts/evaluate_leads.py --apply-decisions
```

### Review queue

Candidates the judge marks "unsure" land in `data/review_queue.json`. Adjudicate them with the `/review-leads` Claude Code skill, or manually edit the file and run `--apply-decisions`.

## Method 2: Chrome Extension (Sales Nav)

Semi-automated extraction from LinkedIn Sales Navigator search results.

### Setup

1. Start local server: `python scripts/serve.py` (runs on 127.0.0.1:8765)
2. Load extension: `chrome://extensions` → Developer mode → Load unpacked → `extension/`
3. After any extension reload, refresh the LinkedIn tab

### Usage

1. Sales Nav → company or account list → Lead search → filter by title queries from `queries.md`
2. Click **Grab page → CSV** (bottom-right overlay)
3. Extension auto-scrolls, extracts, dedup-appends to the correct contacts CSV, recounts, and auto-advances to next page
4. Repeat until toast says `(last page)`

### Fallback (manual paste)

```bash
pbpaste | python scripts/parse_linkedin.py            # append + recount
pbpaste | python scripts/parse_linkedin.py --json     # preview only
pbpaste | python scripts/parse_linkedin.py --csv <p>  # target specific CSV
```

## Risks

Automating Sales Nav breaks LinkedIn ToS (throttle → ban). Mitigated by: own browser session, DOM-read only, human-paced scroll, manual trigger per page, modest volume.

DuckDuckGo scraping may trigger challenge pages. Fix: run `python scripts/duckduckgo_search.py --show "any query"` to solve the challenge in a visible browser, then resume the batch.
