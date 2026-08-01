---
name: scrape-leads
description: Run the full scrape → evaluate pipeline for one target company.
---

Run the full scrape → evaluate pipeline for one target company.

1. Collect inputs:

Target company:
- Ask the user to type the exact company string from data/companies/*.csv.
- Do NOT use AskUserQuestion for this field.
- Verify the company exists before continuing.

Pages per query:
- Ask the user:
  - 1 page (~6–10 results)
  - 10 pages (~60–70 results)
  - 15 pages (~45–105 results)

2. Generate queries:

Run:

source .venv/bin/activate && python scripts/query_builder.py "<company>" > /tmp/queries.txt

Do not manually construct queries.
query_builder.py handles:
- GTM keyword expansion
- leadership queries
- company normalization
- parenthetical removal
- DDG formatting

3. Run searches (batch mode):

```bash
rm -f /tmp/scrape_*.json
source .venv/bin/activate && python scripts/duckduckgo_search.py --batch --pages <N> /tmp/queries.txt
```

This handles:
- Adaptive delays (4-8s jitter between queries)
- Exponential cooldown on rate-limit (30s → 60s → 120s)
- Early stop after 5 consecutive queries with 0 new URLs
- Resume: re-run the same command to skip already-fetched queries

If DuckDuckGo challenge occurs:

Run:

```bash
python scripts/duckduckgo_search.py --show "any query"
```

Then re-run the batch command (it resumes from where it stopped).

4. Merge:

Run:

python scripts/merge_results.py /tmp/scrape_merged.json

5. Evaluate:

First, find which CSV file the company is in:

```bash
for f in data/companies/*.csv; do
  if grep -q "^[^,]*,.*,${company}," "$f"; then
    industry="${f##*/}"; industry="${industry%.csv}"
    csv_file="data/contacts/${industry}.csv"
    break
  fi
done
```

Then run:

```bash
source .venv/bin/activate && python scripts/evaluate_leads.py --company "<company>" --csv "$csv_file" /tmp/scrape_merged.json
```

6. Summarize:
Report:
- accepted leads
- accepted names/titles
- rejection counts by reason
- unsure queue count
- updated contact count

If unsure candidates exist:

Run /review-leads