---
name: review-leads
description: Adjudicate queued unsure lead candidates from data/review_queue.json and apply the decisions
---

Adjudicate the unsure lead candidates the headless judge queued in `data/review_queue.json`.

1. Read `data/review_queue.json`. If missing or empty, tell the user the queue is clear and stop.
2. Present candidates for adjudication with AskUserQuestion, up to 4 per call. One question per candidate: header = candidate name, question shows the title, the snippet's role/employer evidence, and the judge's lean (`lean.reason`, `lean.evidence`). Options: "Accept — NA", "Accept — Global", "Reject" (each with a one-line description of what the evidence supports).
3. Build a decisions array: `{url, verdict: "yes"|"no", category: "na"|"global" (yes only), csv_title, reason}`. For `csv_title` use `lean.csv_title` if present, else copy the job title verbatim from the snippet. For rejects, reason is a short code (client_serving, wrong_company, not_marketing_role, other_region...).
4. Write it to `/tmp/review_decisions.json`, then run:
   `source .venv/bin/activate && python scripts/evaluate_leads.py --apply-decisions /tmp/review_decisions.json`
   This appends accepts to the contacts CSV, recounts, logs verdicts, records each ruling in `data/golden.jsonl`, and removes adjudicated items from the queue. Skipped candidates stay queued.
5. Report what was added/rejected. If the user's rulings show a recurring pattern the rubric misses, propose a new worked example for `scripts/rubric.md` (bump `version:`), and after any rubric edit run `python scripts/evaluate_leads.py --check`.
