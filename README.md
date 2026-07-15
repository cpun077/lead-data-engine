# lead-data-engine

Company lists + their GTM/revenue contacts, as CSVs.

- `data/companies/<industry>.csv` — `category, rank, company, [segment,] domain, contact_count`
- `data/contacts/<industry>.csv` — `company, name, title`
- Contact → company link is by **exact `company` name** (drives routing, dedup, counts)
- Column defs: `schema/companies.md`, `schema/contacts.md`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate    # each new terminal
```

Stdlib only — nothing to install.

## Collect contacts

1. **Server** (once per session): `python scripts/serve.py` — leave running (127.0.0.1:8765)
2. **Extension** (once): `chrome://extensions` → Developer mode → Load unpacked → `extension/`
   - After any extension reload, **refresh the LinkedIn tab**
3. **Search**: Sales Nav → add company to an account list → Lead search → account-list filter + a query from `queries.md` → run
4. **Grab**: click **Grab page → CSV** (bottom-right). It auto-scrolls, extracts, saves (dedup), recounts, and auto-advances. Repeat until toast says `(last page)`.

Data lands in `data/contacts/<industry>.csv` automatically.

## Company classification (auto-detected)

- **Single-company search** (Current-company filter set): all contacts stamped with that company; different-role cards kept but title-flagged `(title unknown — multiple roles): …`
- **Multi-company search** (account list, no company filter): each contact keeps its own card company; nothing flagged

⚠️ Matching is **exact**. A card company ≠ list name (`A.T. Kearney` vs `Kearney`) falls to the default CSV uncounted. Fix: scrape single-company, or align the list name to LinkedIn's brand first. (Fuzzy matching was removed — caused collisions like Kearney ↔ Kearney & Co.)

## Check data

```bash
grep -c , data/contacts/consulting_tier2.csv     # rows incl. header
grep "OC&C" data/companies/consulting_tier2.csv  # a count
python scripts/recount_contacts.py               # rebuild all counts
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Button dead / "server running?" | start `python scripts/serve.py` |
| "Extension context lost" | reload extension → refresh tab |
| "Only N cards" / "missing title" | LinkedIn DOM changed → update `data-anonymize` selectors in `content.js` |
| Missed leads (scrolled fast) | raise the delay in `autoScroll()` |
| Wrong CSV | company name didn't match a list row → see exact-match note above |

## Manual paste (fallback)

Cmd+A the results page, copy, then:

```bash
cd scripts
pbpaste | python parse_linkedin.py            # append + recount
pbpaste | python parse_linkedin.py --json     # preview, no write
pbpaste | python parse_linkedin.py --csv <p>  # specific CSV
```

## Safety

Automating Sales Nav breaks LinkedIn's ToS (risk: throttle → ban). Mitigated by: own browser + session, DOM-read only, human-paced scroll, manual Grab per page. Keep volume modest.

## Layout

```
data/companies/   one CSV per industry — one row per company
data/contacts/    mirrors companies/ — GTM people
data/raw/         original combined dump
extension/        Chrome extension — see extension/README.md
schema/           column defs
scripts/          serve.py · parse_linkedin.py · recount_contacts.py
queries.md        Sales Nav title queries by segment
```

GTM/revenue = sales, marketing, bizdev, partnerships, CS, and the revenue leadership above them.
