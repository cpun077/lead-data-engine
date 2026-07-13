# lead-data-engine

Company lists and their GTM / revenue-generation contacts, stored as CSVs.

- `data/companies/<industry>.csv` — one row per company: `category, rank, company, domain, contact_count`
- `data/contacts/<industry>.csv` — GTM people, one row per person: `company, name, title`
- A contact links to its company by **exact `company` name** (this drives routing, dedup, and `contact_count`).

Full column definitions: `schema/companies.md`, `schema/contacts.md`.

---

## One-time setup

```bash
python3 -m venv .venv          # create the local virtualenv
source .venv/bin/activate      # activate it (do this each new terminal)
```

No dependencies to install — the scripts use only the Python standard library.

---

## Collecting contacts (the normal workflow)

You collect contacts one company at a time from LinkedIn Sales Navigator, using
the Chrome extension + a local server. The extension grabs each results page and
the server writes it to the right CSV.

### Step 1 — Start the server (once per session)

In the repo, with the venv active:

```bash
python scripts/serve.py
```

Leave this terminal running. It listens on `http://127.0.0.1:8765` and prints
each save.

### Step 2 — Load the Chrome extension (once ever)

1. Open `chrome://extensions`
2. Turn on **Developer mode** (top-right toggle)
3. Click **Load unpacked** and select the `extension/` folder

You only redo this if you change the extension code — and after any reload,
**refresh the LinkedIn tab.**

### Step 3 — Set up your Sales Navigator search (once per company)

1. In Sales Nav, find the company under **Accounts** and add it to your account list.
2. Go to **Lead** search, add that account list as a filter.
3. Add your job-title query, e.g.:
   ```
   ("Partner" OR "Managing Partner" OR "Associate Partner" OR "Director" OR "Managing Director" OR "Vice President" OR "VP")
   AND NOT ("Assistant" OR "HR" OR "Talent" OR "IT" OR "Operations" OR "Marketing" OR "Recruiter" OR "Research" OR "Consultant" OR "Intern")
   ```
4. Run the search so a results page is showing (`.../sales/search/people?...`).

### Step 4 — Grab the pages

On the results page, click the blue **Grab page → CSV** button (bottom-right).
Each click:

1. Auto-scrolls to load all ~25 leads on the page
2. Extracts each lead (name, title) and stamps the company
3. Saves them (skipping duplicates) and updates `contact_count`
4. **Auto-advances to the next page**

Then just **click Grab again** on the new page. Repeat until the toast says
`(last page)`.

The toast after each grab shows:
```
<Company>
+N added, M skipped → <file>.csv
→ next page        (or "(last page)")
```

That's it — the data lands in `data/contacts/<industry>.csv` automatically.

---

## Checking your data

```bash
grep -c , data/contacts/consulting_tier2.csv       # contacts collected (incl. header)
grep "OC&C" data/companies/consulting_tier2.csv    # a company's contact_count
python scripts/recount_contacts.py                 # rebuild all contact_counts
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Button does nothing / "Is the local server running?" | Start `python scripts/serve.py` |
| "Extension context lost — refresh this page" | Reload extension → **refresh the LinkedIn tab** |
| "Only N cards extracted" / "missing a title" warning | LinkedIn changed its DOM — the `data-anonymize` selectors in `extension/content.js` need updating |
| Scrolled too fast / missed leads | Already tuned to load slowly; if still short, increase the delay in `autoScroll()` |
| Contacts went to the wrong CSV | The company name didn't exactly match any `data/companies/*.csv` row, so it fell back to the default. Fix the company name or add it to a list. |

---

## Manual paste (fallback, no extension)

If the extension breaks, you can still parse a page by hand: select all on the
results page (Cmd+A), copy, then:

```bash
cd scripts
pbpaste | python parse_linkedin.py                 # append + recount
pbpaste | python parse_linkedin.py --json          # preview only, no writes
pbpaste | python parse_linkedin.py --csv <path>    # write to a specific CSV
```

Default destination is `DEFAULT_CSV` at the top of `scripts/parse_linkedin.py`.

---

## Safety

Automating Sales Navigator violates LinkedIn's User Agreement and risks account
throttling or restriction. This tooling limits (does not eliminate) that risk by
running inside your own logged-in browser, reading the page DOM only, scrolling
at a human-like pace, and requiring you to click **Grab** for every page. Keep
your volume modest and human-paced.

---

## Layout

```
data/
  companies/   one CSV per industry list — one row per company
  contacts/    one CSV per industry, mirroring companies/ — GTM people
  raw/         original combined source dump
extension/     Chrome extension (grabs Sales Nav pages)  — see extension/README.md
schema/        column definitions for companies and contacts
scripts/       serve.py (receiver), parse_linkedin.py (parser), recount_contacts.py
```

"GTM / revenue-generation" = sales, marketing, bizdev, partnerships, customer
success, and the revenue leadership above them. See `schema/contacts.md`.
