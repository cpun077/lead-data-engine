import re


GTM_TERMS = [
    "marketing",
    "communications",
    "brand",
    "content",
    "PR",
    "public relations",
    "media relations",
    "go-to-market",
    "CRM",
    "media",
    "business development",
    "audience",
    "events",
    "engagement",
    "growth"
]


LEADERSHIP_TERMS = [
    "chief marketing officer",
    "CMO",
    "head of marketing",
    "head of communications",
    "marketing leader",
    "communications leader",
    "global marketing",
    "global communications",
    "firmwide marketing",
]


def strip_parenthetical(company):
    return re.sub(r"\s*\([^)]*\)", "", company).strip()


def build_queries(company, mode="standard"):
    queries = []
    clean_company = strip_parenthetical(company)

    if mode == "standard":
        for term in LEADERSHIP_TERMS:
            queries.append(
                f'site:linkedin.com/in "{clean_company}" {term}'
            )

        for term in GTM_TERMS:
            queries.append(
                f'site:linkedin.com/in "{company}" global {term}'
            )
            queries.append(
                f'site:linkedin.com/in "{company}" {term} united states'
            )

    return queries


if __name__ == "__main__":
    import sys

    company = sys.argv[1]

    for q in build_queries(company):
        print(q)
