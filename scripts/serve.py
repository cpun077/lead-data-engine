#!/usr/bin/env python3
"""Local receiver for the Sales Navigator extractor Chrome extension.

Listens on 127.0.0.1:8765 and accepts:

    POST /contacts   body: [{"company", "name", "title"}, ...]

For each posted batch it routes contacts to the right per-industry CSV (by
matching `company` against data/companies/*.csv), appends them (deduped) via
parse_linkedin.append_to_csv, refreshes contact_count for the touched companies
via recount_contacts.update_counts, and replies with a JSON summary.

    python scripts/serve.py            # start on 127.0.0.1:8765
    python scripts/serve.py 9000       # start on a different port

Loopback-only, single-threaded, no external deps. No CORS handling: the Chrome
extension POSTs from its background service worker, which is exempt from page
CORS / Private Network Access, so browsers never send a preflight here.

Note: binding loopback is not access control — any local process can POST. That
is an accepted tradeoff for a solo tool.
"""
import csv
import glob
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
COMPANIES_DIR = os.path.join(REPO_ROOT, "data", "companies")
CONTACTS_DIR = os.path.join(REPO_ROOT, "data", "contacts")

sys.path.insert(0, SCRIPT_DIR)
import parse_linkedin
import recount_contacts

HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def build_company_index():
    """Map company name -> contacts CSV path, using the companies lists as the
    routing table. Files are scanned in sorted filename order, first match wins
    (deterministic tie-break for companies that appear in more than one list).
    """
    index = {}
    for companies_csv in sorted(glob.glob(os.path.join(COMPANIES_DIR, "*.csv"))):
        contacts_csv = os.path.join(CONTACTS_DIR, os.path.basename(companies_csv))
        with open(companies_csv, newline="") as f:
            for row in csv.DictReader(f):
                name = (row.get("company") or "").strip()
                if name and name not in index:
                    index[name] = contacts_csv
    return index


def route(company, index):
    """Resolve a company to its contacts CSV, falling back to DEFAULT_CSV."""
    target = index.get(company.strip())
    if target is None:
        print(f"WARNING: '{company}' not found in any companies list — "
              f"routing to default ({os.path.basename(parse_linkedin.DEFAULT_CSV)})",
              file=sys.stderr)
        return parse_linkedin.DEFAULT_CSV
    return target


def handle_contacts(contacts):
    """Append contacts to their routed CSVs and recount. Returns a summary dict."""
    index = build_company_index()

    # Group by target CSV so each file is rewritten once.
    by_target = {}
    for c in contacts:
        by_target.setdefault(route(c["company"], index), []).append(c)

    added = skipped = 0
    targets = []
    for target, group in by_target.items():
        a, s, _ = parse_linkedin.append_to_csv(group, target)
        added += a
        skipped += s
        targets.append(os.path.basename(target))

    touched = {c["company"] for c in contacts}
    recount_contacts.update_counts(only=touched)

    return {"added": added, "skipped": skipped, "total": len(contacts),
            "target": ", ".join(sorted(set(targets)))}


class Handler(BaseHTTPRequestHandler):
    def _json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.rstrip("/") != "/contacts":
            self._json(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            contacts = json.loads(self.rfile.read(length) or b"[]")
        except (ValueError, json.JSONDecodeError) as e:
            self._json(400, {"error": f"bad request body: {e}"})
            return

        # Empty-payload guard (own check — never sys.exit inside the server).
        if not isinstance(contacts, list) or not contacts:
            self._json(400, {"error": "no contacts in payload"})
            return

        try:
            summary = handle_contacts(contacts)
        except Exception as e:  # keep the server alive across bad posts
            print(f"ERROR handling POST: {e}", file=sys.stderr)
            self._json(500, {"error": str(e)})
            return

        print(f"POST /contacts -> {summary}", file=sys.stderr)
        self._json(200, summary)

    def log_message(self, *args):  # silence default access logging
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    server = HTTPServer((HOST, port), Handler)  # single-threaded on purpose
    print(f"lead-data-engine receiver listening on http://{HOST}:{port}/contacts")
    print(f"default target: {parse_linkedin.DEFAULT_CSV}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        server.server_close()


if __name__ == "__main__":
    main()
