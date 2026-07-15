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
HOST, DEFAULT_PORT = "127.0.0.1", 8765

sys.path.insert(0, SCRIPT_DIR)
import parse_linkedin
import recount_contacts


def company_index():
    index = {}
    for companies_csv in sorted(glob.glob(os.path.join(COMPANIES_DIR, "*.csv"))):
        contacts_csv = os.path.join(CONTACTS_DIR, os.path.basename(companies_csv))
        with open(companies_csv, newline="") as f:
            for row in csv.DictReader(f):
                name = (row.get("company") or "").strip()
                if name:
                    index.setdefault(name, contacts_csv)
    return index


def handle_contacts(contacts):
    index = company_index()
    by_target = {}
    for c in contacts:
        target = index.get(c["company"].strip(), parse_linkedin.DEFAULT_CSV)
        by_target.setdefault(target, []).append(c)

    added = skipped = 0
    for target, group in by_target.items():
        a, s, _ = parse_linkedin.append_to_csv(group, target)
        added += a
        skipped += s
    recount_contacts.update_counts(only={c["company"] for c in contacts})
    return {"added": added, "skipped": skipped, "total": len(contacts),
            "target": ", ".join(sorted(os.path.basename(t) for t in by_target))}


class Handler(BaseHTTPRequestHandler):
    def _json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.rstrip("/") != "/contacts":
            return self._json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            contacts = json.loads(self.rfile.read(length) or b"[]")
        except ValueError as e:
            return self._json(400, {"error": f"bad body: {e}"})
        if not isinstance(contacts, list) or not contacts:
            return self._json(400, {"error": "no contacts in payload"})
        try:
            summary = handle_contacts(contacts)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return self._json(500, {"error": str(e)})
        print(f"POST /contacts -> {summary}", file=sys.stderr)
        self._json(200, summary)

    def log_message(self, *args):
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    server = HTTPServer((HOST, port), Handler)
    print(f"listening on http://{HOST}:{port}/contacts")
    print(f"default target: {parse_linkedin.DEFAULT_CSV}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
