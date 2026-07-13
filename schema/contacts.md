# Contacts schema

GTM / revenue-generation people, one row per person. Files live in
`data/contacts/` and **mirror `data/companies/` one-to-one by filename**
(e.g. contacts for firms in `companies/amlaw.csv` go in `contacts/amlaw.csv`).

Linked to a company by `company` name (which should match `companies.company`).

Scope = people who generate or drive revenue: sales, marketing, business
development, partnerships, customer success, and the revenue-leadership layer
above them (CRO, CMO, Chief Growth/Revenue Officer, Head of Sales, etc.).
Exclude delivery/ops/engineering/finance unless they own a revenue number.

| Column    | Description                                        |
|-----------|----------------------------------------------------|
| `company` | Company name (matches `companies.company`).        |
| `name`    | Person's full name.                                |
| `title`   | Job title from the source.                         |
