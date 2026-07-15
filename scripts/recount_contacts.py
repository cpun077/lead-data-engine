import csv
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPANIES = os.path.join(ROOT, "data", "companies")
CONTACTS = os.path.join(ROOT, "data", "contacts")


def contact_counts():
    counts = {}
    for path in glob.glob(os.path.join(CONTACTS, "*.csv")):
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                name = (row.get("company") or "").strip()
                if name:
                    counts[name] = counts.get(name, 0) + 1
    return counts


def update_counts(only=None):
    counts = contact_counts()
    for path in glob.glob(os.path.join(COMPANIES, "*.csv")):
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
            fields = list(rows[0].keys()) if rows else []
        touched = [r for r in rows if only is None or r["company"].strip() in only]
        if not touched:
            continue
        for row in touched:
            row["contact_count"] = counts.get(row["company"].strip(), 0)
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print(f"{os.path.basename(path)}: {len(touched)} company row(s) updated")


def main():
    update_counts()
    print(f"total contacts counted: {sum(contact_counts().values())}")


if __name__ == "__main__":
    main()
