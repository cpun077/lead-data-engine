#!/usr/bin/env python3
"""Recompute `contact_count` in data/companies/*.csv from data/contacts/*.csv.

`contact_count` is a derived field (number of contact rows per company name).

    python3 scripts/recount_contacts.py                 # recount every company
    recount_contacts.update_counts({"Acme Inc"})        # only the given companies

The extraction script calls update_counts() with just the companies it touched,
so a single paste only rewrites the affected company row/file.
"""
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
            reader = csv.DictReader(f)
            for row in reader:
                company = (row.get("company") or "").strip()
                if company:
                    counts[company] = counts.get(company, 0) + 1
    return counts


def update_counts(only=None):
    """Update contact_count in the company CSVs.

    If `only` is a set of company names, only those rows are touched (and only
    files containing them are rewritten). If None, every company is recounted.
    """
    counts = contact_counts()
    for path in glob.glob(os.path.join(COMPANIES, "*.csv")):
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
            fields = list(rows[0].keys()) if rows else []
        touched = 0
        for row in rows:
            name = row["company"].strip()
            if only is not None and name not in only:
                continue
            row["contact_count"] = counts.get(name, 0)
            touched += 1
        if touched == 0:
            continue  # nothing in this file changed; leave it untouched
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        print(f"{os.path.basename(path)}: {touched} company row(s) updated")


def main():
    update_counts(only=None)
    print(f"total contacts counted: {sum(contact_counts().values())}")


if __name__ == "__main__":
    main()
