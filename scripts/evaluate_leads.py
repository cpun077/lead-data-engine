import contextlib
import csv
from concurrent.futures import ThreadPoolExecutor
import html
import json
import os
import re
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
RUBRIC = os.path.join(SCRIPT_DIR, "rubric.md")
LOG = os.path.join(ROOT, "data", "eval_log.jsonl")
QUEUE = os.path.join(ROOT, "data", "review_queue.json")
GOLDEN = os.path.join(ROOT, "data", "golden.jsonl")

sys.path.insert(0, SCRIPT_DIR)
import parse_linkedin
import recount_contacts

OTHER_REGIONS = re.compile(
    r"\b(emea|europe|uk|united kingdom|apac|asia|asia[- ]pacific|india|middle east|"
    r"africa|australia|japan|china|germany|france|iberia|nordics|benelux|dach)\b", re.I)
BLOCKED = re.compile(
    r"\b(summer|intern|co[- ]?op|senior director|analyst|consultant|talent|principal|learner|"
    r"senior advis[eo]r|senior associate|hr|human resources|assistant|student|consumer|"
    r"strategist|marketing associate|employer|client capabilities|category manager|"
    r"leadership programs|senior partner|practice manager|strategy & operations|"
    r"media services|alumni|advisory board|engagement manager|lawyer|attorney|counsel|litigation|practice chair"
    r"coach|training|learning|learning & development|recruiting|trainer|database|"
    r"internal communications|internal engagement|employee engagement|billing|"
    r"social responsibility|corporate social responsibility|csr|cloud|"
    r"travel|meetings|events technology|editor|acquisitions|intranet|practice innovation|"
    r"change|strategic communications|graphics|expert manager|expert senior manager|graphic designer|"
    r"university|campus)\b",
    re.I
)
GLOBAL = re.compile(r"\b(chief|global)\b", re.I)
CSUITE = re.compile(
    r"\b(chief (marketing|communications?|brand|content|growth|client|business development|revenue) officer|cmo|"
    r"(head|leader|lead) of (global )?(marketing|communications?|brand|content|pr|public relations|business development|revenue)|"
    r"(marketing|communications?|brand|content|business development) (head|leader|lead)\b)", re.I)
EXPERIENCE = re.compile(r"Experience:\s*([^·\n]+)")
RV = re.search(r"version:\s*(\S+)", open(RUBRIC).read()).group(1)


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z\s]", "", s.lower())).strip()


def existing_names(csv_path, company):
    names = set()
    if os.path.exists(csv_path):
        with open(csv_path, newline="") as f:
            for row in csv.DictReader(f):
                if row["company"].strip() == company:
                    names.add(norm(row["name"]))
    return names


def is_dup(name, names):
    n = norm(name)
    return any(n == e or n.startswith(e + " ") or e.startswith(n + " ") for e in names)


def name_matches_company(name, company):
    parts = set(norm(company).split()) - {"and", "the", "of", "llp", "llc", "inc", "company"}
    name_parts = set(norm(name).split())
    overlap = parts & name_parts
    return any(len(p) > 5 for p in overlap) or len(overlap) >= 2


def rules(r, company):
    title = r["title"]
    snippet = r["snippet"]

    name = r.get("name", title.split(" - ", 1)[0])
    if name_matches_company(name, company):
        return "no", "name_company_confusion"
    if BLOCKED.search(title.split(" - ", 1)[-1]) and not CSUITE.search(title + " " + snippet):
        return "no", "blocked_title"
    if OTHER_REGIONS.search(title) and not GLOBAL.search(title):
        return "no", "other_region"
    m = EXPERIENCE.search(snippet)
    if m and norm(company) not in norm(m.group(1)):
        return "no", "wrong_company"
    return None


def triage(results, company, csv_path):
    names = existing_names(csv_path, company)
    seen, candidates, logs = set(), [], []
    for r in sorted(results, key=lambda r: r.get("url", "")):
        e = {"company": company,
             "url": r.get("url", ""),
             "title": html.unescape(r.get("title", "")),
             "snippet": html.unescape(r.get("snippet", ""))}
        e["name"] = e["title"].split(" - ")[0].strip()
        if "linkedin.com/in" not in e["url"]:
            v = ("no", "not_profile", "filter")
        elif e["url"] in seen or is_dup(e["name"], names):
            v = ("no", "duplicate", "filter")
        else:
            ruled = rules(e, company)
            v = ruled + ("rules",) if ruled else None
        seen.add(e["url"])
        if v:
            logs.append({**e, "verdict": v[0], "reason": v[1], "stage": v[2]})
        else:
            candidates.append(e)
    return candidates, logs


def judge_chunk(chunk, company, rubric):
    payload = [{k: c[k] for k in ("url", "title", "snippet")} for c in chunk]
    prompt = (rubric + f"\nTarget company: {company}\nCandidates:\n"
              + json.dumps(payload, ensure_ascii=False) + "\n\nRespond with ONLY the JSON array, no other text.")
    for _ in range(2):
        try:
            out = subprocess.run(
                ["claude", "-p", prompt, "--model", "us.anthropic.claude-haiku-4-5-20251001-v1:0", "--output-format", "json"],
                capture_output=True, text=True, timeout=300)
            parsed = json.loads(out.stdout)
            result_str = parsed.get("result", "")
            m = re.search(r"\[.*\]", result_str, re.S)
            if not m:
                continue
            items = json.loads(m.group(0))
            result = {}
            for v in items:
                if v.get("url") and all(k in v for k in ("verdict", "reason")):
                    result[v["url"]] = v
            return result if result else None
        except Exception:
            continue
    return None


def judge(cands, company):
    rubric = open(RUBRIC).read()
    chunks = [cands[i:i + 20] for i in range(0, len(cands), 20)]
    verdicts = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        for result in ex.map(lambda c: judge_chunk(c, company, rubric), chunks):
            if result:
                verdicts.update(result)
    return verdicts or None


def _norm_ws(s):
    return re.sub(r"\s+", " ", html.unescape(s)).strip().lower()


def validate(c, v):
    hay = _norm_ws(c["title"] + " " + c["snippet"])
    if not v or v.get("verdict") not in ("yes", "no", "unsure"):
        return None
    if v["verdict"] == "yes":
        if v.get("category") not in ("global", "na"):
            return None
        if not v.get("csv_title") or _norm_ws(v["csv_title"]) not in hay:
            return None
        if v.get("evidence"):
            parts = [_norm_ws(p) for p in v["evidence"].split("·") if p.strip()]
            if parts and not all(p in hay for p in parts):
                return None
    reason = v.get("reason", "")
    if v["verdict"] != "yes" and not reason:
        reason = "ambiguous_role" if v["verdict"] == "unsure" else "no_role_evidence"
    return {"verdict": v["verdict"], "reason": reason,
            "category": v.get("category") if v["verdict"] == "yes" else None,
            "csv_title": v.get("csv_title", ""), "evidence": v.get("evidence", "")}


def write_logs(entries, dry):
    for e in entries:
        e.update(ts=time.strftime("%Y-%m-%dT%H:%M:%S"), rubric_version=RV)
        print(json.dumps(e, ensure_ascii=False))
    if not dry and entries:
        with open(LOG, "a") as f:
            f.writelines(json.dumps(e, ensure_ascii=False) + "\n" for e in entries)


def write_queue(items, dry):
    if dry or not items:
        return
    queue = json.load(open(QUEUE)) if os.path.exists(QUEUE) else []
    urls = {q["url"] for q in queue}
    queue += [i for i in items if i["url"] not in urls]
    json.dump(queue, open(QUEUE, "w"), ensure_ascii=False, indent=2)


def apply_rows(rows, csv_path, dry):
    if dry or not rows:
        return
    added, skipped, total = parse_linkedin.append_to_csv(rows, csv_path)
    print(f"{os.path.basename(csv_path)}: +{added} added, {skipped} skipped, {total} total",
          file=sys.stderr)
    with contextlib.redirect_stdout(sys.stderr):
        recount_contacts.update_counts(only={r["company"] for r in rows})


def _process_judged(candidates, verdicts, logs, rows, queued, company):
    skipped = []
    for c in candidates:
        raw = verdicts.get(c["url"])
        v = validate(c, raw)
        if v is None and raw is None:
            skipped.append(c)
            continue
        if v is None:
            v = {"verdict": "unsure", "reason": "invalid_judge_output", "category": None,
                 "csv_title": "", "evidence": ""}
        logs.append({**c, **v, "stage": "judge"})
        if v["verdict"] == "yes":
            rows.append({"company": company, "name": c["name"], "title": v["csv_title"]})
        elif v["verdict"] == "unsure":
            queued.append({**c, "lean": v})
    return skipped


def evaluate(results, company, csv_path, dry):
    candidates, logs = triage(results, company, csv_path)
    rows, queued = [], []
    for log in logs:
        if log.get("verdict") == "yes" and log.get("stage") == "rules":
            title = log["title"].split(" - ", 1)[-1].replace(" | LinkedIn", "").strip() if " - " in log["title"] else log["title"]
            rows.append({"company": company, "name": log["name"], "title": title})
    if candidates:
        verdicts = judge(candidates, company) or {}
        skipped = _process_judged(candidates, verdicts, logs, rows, queued, company)
        if skipped:
            rubric = open(RUBRIC).read()
            retry_chunks = [skipped[i:i + 10] for i in range(0, len(skipped), 10)]
            retry_verdicts = {}
            with ThreadPoolExecutor(max_workers=10) as ex:
                for result in ex.map(lambda c: judge_chunk(c, company, rubric), retry_chunks):
                    if result:
                        retry_verdicts.update(result)
            _process_judged(skipped, retry_verdicts, logs, rows, queued, company)
    write_logs(sorted(logs, key=lambda e: e["url"]), dry)
    write_queue(queued, dry)
    apply_rows(rows, csv_path, dry)


def apply_decisions(path, csv_path, dry):
    queue = json.load(open(QUEUE)) if os.path.exists(QUEUE) else []
    by_url = {q["url"]: q for q in queue}
    logs, rows, golden = [], [], []
    for d in json.load(open(path)):
        q = by_url.pop(d["url"], None)
        if not q:
            continue
        q.pop("lean", None)
        logs.append({**q, "verdict": d["verdict"], "reason": d.get("reason", ""),
                     "category": d.get("category"), "stage": "human"})
        golden.append({"company": q["company"],
                       "input": {k: q[k] for k in ("url", "title", "snippet")},
                       "expect": {"verdict": d["verdict"], "category": d.get("category")}})
        if d["verdict"] == "yes":
            rows.append({"company": q["company"], "name": q["name"], "title": d["csv_title"]})
    write_logs(logs, dry)
    if not dry:
        with open(GOLDEN, "a") as f:
            f.writelines(json.dumps(g, ensure_ascii=False) + "\n" for g in golden)
        json.dump(list(by_url.values()), open(QUEUE, "w"), ensure_ascii=False, indent=2)
    by_csv = {}
    for r in rows:
        target = parse_linkedin.find_company_csv(r["company"]) or csv_path
        by_csv.setdefault(target, []).append(r)
    for target, group in by_csv.items():
        apply_rows(group, target, dry)


def check():
    golden = [json.loads(l) for l in open(GOLDEN)]
    rubric = open(RUBRIC).read()
    by_company = {}
    for g in golden:
        g["input"] = {k: html.unescape(v) for k, v in g["input"].items()}
        ruled = rules(g["input"], g["company"])
        g["got"] = {"verdict": ruled[0], "category": None} if ruled else None
        if not g["got"]:
            by_company.setdefault(g["company"], []).append(g["input"])
    chunks = [(c, inputs[i:i + 10]) for c, inputs in by_company.items()
              for i in range(0, len(inputs), 10)]
    verdicts = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        for r in ex.map(lambda ch: judge_chunk(ch[1], ch[0], rubric), chunks):
            if r:
                verdicts.update(r)
    fails = 0
    for g in golden:
        if not g["got"]:
            v = validate(g["input"], verdicts.get(g["input"]["url"]))
            if v is None:
                v = {"verdict": "unsure", "category": None}
            g["got"] = {"verdict": v["verdict"], "category": v.get("category")}
        exp, got = g["expect"], g["got"]
        ok = got["verdict"] == "unsure" or (
            exp["verdict"] == got["verdict"] and (
                exp["verdict"] != "yes" or exp.get("category") == got.get("category")))
        if not ok:
            fails += 1
            print(f"MISMATCH {g['input']['url']}: expected {exp}, got {got}")
    print(f"{len(golden) - fails}/{len(golden)} golden cases pass (judge unsure tolerated)")
    sys.exit(1 if fails else 0)


def main():
    args = sys.argv[1:]
    if "--check" in args:
        return check()
    dry = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    opts = {}
    for flag in ("--company", "--csv", "--apply-decisions"):
        if flag in args:
            i = args.index(flag)
            opts[flag] = args[i + 1]
            del args[i:i + 2]
    if "--csv" not in opts and "--company" in opts:
        found = parse_linkedin.find_company_csv(opts["--company"])
        if found:
            opts["--csv"] = found
    csv_path = opts.get("--csv", parse_linkedin.DEFAULT_CSV)
    if "--apply-decisions" in opts:
        return apply_decisions(opts["--apply-decisions"], csv_path, dry)
    if "--company" not in opts:
        sys.exit('usage: evaluate_leads.py --company "<name>" [--csv path] [--dry-run] [file] '
                 '| --apply-decisions file | --check')
    results = json.loads(open(args[0]).read() if args else sys.stdin.read())
    evaluate(results, opts["--company"], csv_path, dry)


if __name__ == "__main__":
    main()
