import csv
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_CSV = os.path.join(REPO_ROOT, "data", "contacts", "consulting_tier2.csv")
FIELDS = ["company", "name", "title"]
GOTO = re.compile(r"Go to (.+?)['’‘]s? profile")

sys.path.insert(0, SCRIPT_DIR)
import recount_contacts


def detect_company(lines):
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

    title_re = re.compile(r"^(.*?)\s{2,}" + re.escape(company) + r"\s*$")
    contacts, seen = [], set()
    for i, line in enumerate(lines):
        m = GOTO.search(line)
        if not m:
            continue
        name = m.group(1).strip()
        title = ""
        for nxt in lines[i + 1:]:
            if GOTO.search(nxt):
                break
            tm = title_re.match(nxt)
            if tm and tm.group(1).strip():
                title = tm.group(1).strip()
                break
        if name and name not in seen:
            seen.add(name)
            contacts.append({"company": company, "name": name, "title": title})
    return contacts


def append_to_csv(contacts, path):
    rows, existing = [], set()
    if os.path.exists(path):
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                rows.append(row)
                existing.add((row["company"].strip(), row["name"].strip()))

    added = skipped = 0
    for c in contacts:
        key = (c["company"].strip(), c["name"].strip())
        if key in existing:
            skipped += 1
            continue
        existing.add(key)
        rows.append(c)
        added += 1

    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
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

    contacts = parse(open(args[0]).read() if args else sys.stdin.read())
    if not contacts:
        sys.exit("WARNING: parsed 0 contacts — nothing written.")

    if json_only:
        print(json.dumps(contacts, ensure_ascii=False, indent=2))
        return
    added, skipped, total = append_to_csv(contacts, csv_path)
    print(f"{os.path.basename(csv_path)}: +{added} added, {skipped} skipped, {total} total",
          file=sys.stderr)
    recount_contacts.update_counts(only={c["company"] for c in contacts})


if __name__ == "__main__":
    main()
