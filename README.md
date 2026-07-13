# lead-data-engine

Company lists and their GTM / revenue-generation contacts.

## Setup

Dependencies live in a local virtual environment (not global):

```bash
python3 -m venv .venv                       # one-time
.venv/bin/pip install -r requirements.txt   # when deps exist
```

Activate it once per terminal session so `python` points at the venv:

```bash
source .venv/bin/activate
```

The `.venv/` dir is git-ignored. (Scripts currently use only the standard
library, so the venv works out of the box.) If you'd rather not activate, call
the interpreter directly instead: `.venv/bin/python scripts/parse_linkedin.py`.

## Extracting contacts

`scripts/parse_linkedin.py` turns a raw LinkedIn Sales Navigator page paste into
contact rows. It strips all nav/filter/footer chrome and keys off two anchors per
result card (`Go to <name>'s profile` and the title line ending in the company
name), auto-detecting the company from the "Current company" filter.

**Workflow** — copy a Sales Navigator results page (Cmd+C), then from `scripts/`:

```bash
cd scripts
pbpaste | python parse_linkedin.py
```

This parses the clipboard, appends new contacts to the default CSV
(`data/contacts/consulting_tier2.csv`, set as `DEFAULT_CSV` in the script),
skips any `(company, name)` already present, and recounts `contact_count`
across the company files. Repeat for each page — re-pasting a page you already
did is harmless (dedup skips it).

Options:

```bash
pbpaste | python parse_linkedin.py --json          # preview JSON only, no writes
pbpaste | python parse_linkedin.py --csv <path>    # append to a different CSV
python parse_linkedin.py raw.txt                   # read a file instead of stdin
```

To change the default destination when moving to another industry list, edit
`DEFAULT_CSV` at the top of `scripts/parse_linkedin.py`.

## Layout

```
data/
  companies/   one CSV per industry list — one row per company
  contacts/    one CSV per industry, mirroring companies/ — GTM people
  raw/         original combined source dump
schema/        column definitions for companies and contacts
scripts/       split / extraction / validation code
```

## Model

- A contact links to its company by the **`company` name**, which must match
  `companies.company` exactly (that's how `contact_count` is tallied).
- `data/contacts/<industry>.csv` holds the GTM/revenue people for the companies
  in `data/companies/<industry>.csv`.
- Each company row carries a `contact_count`, kept in sync automatically by the
  extraction script (or manually via `scripts/recount_contacts.py`).
- "GTM / revenue-generation" = sales, marketing, bizdev, partnerships, customer
  success, and the revenue leadership above them. See `schema/contacts.md`.

## Files

See `schema/companies.md` and `schema/contacts.md` for full column definitions.
