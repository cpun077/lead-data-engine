# Sales Nav grabber (Chrome extension)

Grabs the current LinkedIn Sales Navigator **people search** results page into the
local `lead-data-engine` CSVs. Runs entirely inside your own logged-in browser and
POSTs to the local receiver (`scripts/serve.py`) — no credentials stored, no
headless bot, and you advance the pages yourself.

> Automating Sales Navigator is against LinkedIn's User Agreement. Keep usage
> human-paced and modest in volume. See the safety note in the repo README.

## One-time install

1. Start the local receiver (in the repo, with the venv active):
   ```bash
   python scripts/serve.py
   ```
2. Open `chrome://extensions` → toggle **Developer mode** (top right).
3. Click **Load unpacked** → select this `extension/` folder.

## Use

1. In Sales Navigator, run your people search for one company (account list +
   job-title query), so the results page is showing.
2. Click the **Grab page → CSV** button (bottom-right). It auto-scrolls to load
   all leads, extracts them, and saves. A toast shows `+N added, M skipped → file`.
3. Change the `page=` number in the URL to go to the next page and click again.
   Re-grabbing a page is harmless — duplicates are skipped.

## How it fits together

- `content.js` — injects the button, auto-scrolls the results container, extracts
  each lead (`data-anonymize` attributes), determines the canonical company from
  the "Current company" filter (falling back to the most common per-card value),
  and hands the list to the service worker.
- `background.js` — the only piece that fetches the local server. Running from the
  extension context (with `host_permissions`) bypasses page CORS / Private Network
  Access, so `serve.py` needs no CORS handling.
- `scripts/serve.py` — routes contacts to the right industry CSV, dedup-appends,
  and refreshes `contact_count`.

## If the button does nothing / save fails

- **"Is the local server running?"** — start `python scripts/serve.py`.
- **"Only N cards extracted" / "missing a title"** — LinkedIn changed its DOM;
  the `data-anonymize` selectors in `content.js` need updating.
- Nothing to grab — make sure you're on `.../sales/search/people?...` (the match
  pattern in `manifest.json`).
