#!/usr/bin/env python3
"""Strip a LinkedIn Sales Navigator page paste down to just the contacts.

Usage (default: append the clipboard/stdin paste to the tier-2 contacts CSV):
    pbpaste | python parse_linkedin.py                 # append to DEFAULT_CSV + recount
    pbpaste | python parse_linkedin.py --json          # just print JSON, no writes
    pbpaste | python parse_linkedin.py --csv <path>    # append to a different CSV
    python parse_linkedin.py raw.txt                   # read from a file instead of stdin

By default parsed contacts are appended to DEFAULT_CSV, skipping any
(company, name) pair already present, then contact_count is recounted.
Paths resolve relative to this script, so it runs from any working directory.

How it works — it ignores all the nav/filter/footer chrome and keys off two
reliable anchors in each result card:
  1. `Go to <NAME>'s profile`  -> the person's name
  2. the next line ending in the company name (`<TITLE>  <Company>`) -> title
The company name is auto-detected from the "Current company" filter, so this
works for any account, not just OC&C.
"""
import csv
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

# Default destination for parsed contacts (override with --csv <path>).
DEFAULT_CSV = os.path.join(REPO_ROOT, "data", "contacts", "consulting_tier2.csv")

sys.path.insert(0, SCRIPT_DIR)
import recount_contacts

# "Go to Justin Tsang's profile", "Go to Oliver Jones' profile" (curly or straight quote,
# optional trailing "s", optional junk after like "was last active 4 minutes ago")
GOTO = re.compile(r"Go to (.+?)['’‘]s? profile")


def detect_company(lines):
    """The company sits right after 'Expand Current company filter'."""
    for i, line in enumerate(lines):
        if line.strip() == "Expand Current company filter":
            for nxt in lines[i + 1:]:
                if nxt.strip():
                    return nxt.strip()
    return None


def parse(text):
    lines = text.splitlines()
    company = detect_company(lines)
    if not company:
        sys.exit("Could not detect company from 'Current company' filter.")

    # Title lines end with the company name (with any whitespace after it).
    title_re = re.compile(r"^(.*?)\s{2,}" + re.escape(company) + r"\s*$")

    contacts = []
    seen = set()
    i = 0
    while i < len(lines):
        m = GOTO.search(lines[i])
        if not m:
            i += 1
            continue
        name = m.group(1).strip()
        # Find this card's title line: the first company-suffixed line below it,
        # stopping if we hit the next person's card.
        title = ""
        for j in range(i + 1, len(lines)):
            if GOTO.search(lines[j]):
                break
            tm = title_re.match(lines[j])
            if tm and tm.group(1).strip():
                title = tm.group(1).strip()
                break
        if name and name not in seen:
            seen.add(name)
            contacts.append({"company": company, "name": name, "title": title})
        i += 1

    return contacts


FIELDS = ["company", "name", "title"]


def append_to_csv(contacts, path):
    existing = set()
    rows = []
    if os.path.exists(path):
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                rows.append(row)
                existing.add((row["company"].strip(), row["name"].strip()))

    added, skipped = 0, 0
    for c in contacts:
        key = (c["company"].strip(), c["name"].strip())
        if key in existing:
            skipped += 1
            continue
        existing.add(key)
        rows.append(c)
        added += 1

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    return added, skipped, len(rows)


def main():
    args = sys.argv[1:]

    json_only = "--json" in args
    if json_only:
        args.remove("--json")

    csv_path = DEFAULT_CSV
    if "--csv" in args:
        idx = args.index("--csv")
        csv_path = args[idx + 1]
        del args[idx:idx + 2]

    text = open(args[0]).read() if args else sys.stdin.read()
    contacts = parse(text)

    # 0-result guard: don't silently write nothing. Likely the wrong page was
    # copied, only chrome was pasted, or no result cards were present.
    if not contacts:
        print("WARNING: parsed 0 contacts — nothing written. Check that you "
              "copied a Sales Navigator results page (with 'Go to ...'s profile' "
              "cards).", file=sys.stderr)
        sys.exit(1)

    if json_only:
        print(json.dumps(contacts, ensure_ascii=False, indent=2))
    else:
        added, skipped, total = append_to_csv(contacts, csv_path)
        print(f"{os.path.basename(csv_path)}: +{added} added, {skipped} skipped "
              f"(already present), {total} total", file=sys.stderr)
        # Only recount the companies this paste actually touched.
        touched = {c["company"] for c in contacts}
        recount_contacts.update_counts(only=touched)


if __name__ == "__main__":
    main()
