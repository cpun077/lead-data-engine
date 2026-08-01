import json
import os
import random
import sys
import time
import urllib.parse

from playwright.sync_api import sync_playwright

PROFILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".ddg_profile")
RESULTS = "article[data-testid='result'], li[data-layout='organic'] article, #links .result--web"
BLOCK_INDICATORS = "#challenge, .challenge-container, form#challenge-form"
BASE_DELAY = (4, 8)
COOLDOWN_STEPS = [30, 60, 120]
EARLY_STOP_THRESHOLD = 5


def _extract_results(page):
    items = page.eval_on_selector_all(RESULTS, """els => els.map(r => {
        const a = r.querySelector("a[data-testid='result-title-a']") || r.querySelector('h2 a');
        return {
            title: a?.innerText || '',
            url: a?.href || '',
            snippet: r.querySelector("[data-result='snippet'], .result__snippet")?.innerText || ''
        };
    })""")
    seen, out = set(), []
    for it in items:
        if it["url"] and it["url"] not in seen:
            seen.add(it["url"])
            out.append(it)
    return out


def _is_blocked(page):
    return page.query_selector(BLOCK_INDICATORS) is not None


def _wait_for_results(page, headless):
    try:
        page.wait_for_selector(RESULTS, timeout=8000)
        return True
    except Exception:
        pass
    if _is_blocked(page):
        return False
    try:
        page.wait_for_selector(RESULTS, timeout=7000)
        return True
    except Exception:
        return False


def _load_more(page, pages):
    for _ in range(pages - 1):
        btn = page.query_selector("#more-results")
        if not btn:
            break
        n = len(page.query_selector_all(RESULTS))
        try:
            btn.click()
        except Exception:
            # Element may be stale after DOM rebuild; retry with fresh selector
            btn = page.query_selector("#more-results")
            if not btn:
                break
            try:
                btn.click()
            except Exception:
                break
        try:
            page.wait_for_function(
                f'document.querySelectorAll("{RESULTS}").length > {n}', timeout=10000)
        except Exception:
            break


def search(query, pages=1, headless=False, retries=3):
    url = "https://duckduckgo.com/?" + urllib.parse.urlencode({"q": query, "ia": "web"})
    for attempt in range(retries):
        try:
            with sync_playwright() as p:
                ctx = p.firefox.launch_persistent_context(
                    PROFILE, headless=headless, locale="en-US",
                    viewport={"width": 1280, "height": 900})
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                if _wait_for_results(page, headless):
                    _load_more(page, pages)
                    results = _extract_results(page)
                    ctx.close()
                    return results
                if not headless:
                    print("Challenge shown — solve it in the window; waiting up to 5 min...", file=sys.stderr)
                    try:
                        page.wait_for_selector(RESULTS, timeout=300000)
                        _load_more(page, pages)
                        results = _extract_results(page)
                        ctx.close()
                        return results
                    except Exception:
                        ctx.close()
                        sys.exit("Timed out waiting for results.")
                ctx.close()
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        except SystemExit:
            raise
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return []


def batch_search(queries, pages=1, headless=True, output_dir="/tmp"):
    all_urls = set()
    dry_streak = 0
    cooldown_count = 0

    for f in os.listdir(output_dir):
        if f.startswith("scrape_") and f.endswith(".json"):
            try:
                with open(os.path.join(output_dir, f)) as fh:
                    for item in json.load(fh):
                        all_urls.add(item.get("url"))
            except Exception:
                pass

    with sync_playwright() as p:
        ctx = p.firefox.launch_persistent_context(
            PROFILE, headless=headless, locale="en-US",
            viewport={"width": 1280, "height": 900})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        for i, query in enumerate(queries):
            out_path = os.path.join(output_dir, f"scrape_{i}.json")
            if os.path.exists(out_path) and os.path.getsize(out_path) > 2:
                print(f"[{i+1}/{len(queries)}] skip (cached): {query[:60]}", file=sys.stderr)
                continue

            if i > 0:
                delay = random.uniform(*BASE_DELAY)
                time.sleep(delay)

            url = "https://duckduckgo.com/?" + urllib.parse.urlencode({"q": query, "ia": "web"})
            page.goto(url, wait_until="domcontentloaded", timeout=45000)

            if not _wait_for_results(page, headless=True):
                if _is_blocked(page):
                    if cooldown_count >= len(COOLDOWN_STEPS):
                        ctx.close()
                        print(f"\n[!] Blocked after {cooldown_count} cooldowns at query {i+1}/{len(queries)}. "
                              f"Re-run with --show once to solve challenge, then re-run batch.", file=sys.stderr)
                        return
                    wait = COOLDOWN_STEPS[cooldown_count]
                    cooldown_count += 1
                    print(f"[{i+1}/{len(queries)}] rate-limited, cooling down {wait}s...", file=sys.stderr)
                    time.sleep(wait)
                    page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    if not _wait_for_results(page, headless=True):
                        ctx.close()
                        print(f"\n[!] Still blocked after cooldown. Re-run with --show to solve challenge.", file=sys.stderr)
                        return
                else:
                    with open(out_path, "w") as f:
                        json.dump([], f)
                    print(f"[{i+1}/{len(queries)}] 0 results: {query[:60]}", file=sys.stderr)
                    dry_streak += 1
                    if dry_streak >= EARLY_STOP_THRESHOLD:
                        print(f"\n[early stop] {EARLY_STOP_THRESHOLD} consecutive queries with 0 new URLs. "
                              f"{len(all_urls)} unique total.", file=sys.stderr)
                        ctx.close()
                        return
                    continue

            cooldown_count = max(0, cooldown_count - 1)
            _load_more(page, pages)
            results = _extract_results(page)

            new_count = sum(1 for r in results if r["url"] not in all_urls)
            for r in results:
                all_urls.add(r["url"])

            with open(out_path, "w") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            print(f"[{i+1}/{len(queries)}] +{new_count} new ({len(results)} total): {query[:60]}", file=sys.stderr)

            if new_count == 0:
                dry_streak += 1
            else:
                dry_streak = 0

            if dry_streak >= EARLY_STOP_THRESHOLD:
                print(f"\n[early stop] {EARLY_STOP_THRESHOLD} consecutive queries with 0 new URLs. "
                      f"{len(all_urls)} unique total.", file=sys.stderr)
                ctx.close()
                return

        ctx.close()
        print(f"\n[done] {len(queries)} queries, {len(all_urls)} unique URLs.", file=sys.stderr)


def main():
    args = sys.argv[1:]
    headless = "--show" not in args
    pages = 1

    if "--pages" in args:
        i = args.index("--pages")
        pages = int(args[i + 1])
        del args[i:i + 2]

    if "--batch" in args:
        args.remove("--batch")
        args = [a for a in args if a not in ("--headless", "--show")]
        if not args:
            sys.exit('usage: duckduckgo_search.py --batch [--pages N] <queries_file>')
        with open(args[0]) as f:
            queries = [line.strip() for line in f if line.strip()]
        batch_search(queries, pages=pages, headless=headless)
        return

    args = [a for a in args if a not in ("--headless", "--show")]
    if not args:
        sys.exit('usage: duckduckgo_search.py [--show] [--pages N] "<query>"\n'
                 '       duckduckgo_search.py --batch [--pages N] <queries_file>')
    print(json.dumps(search(args[0], pages=pages, headless=headless), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
