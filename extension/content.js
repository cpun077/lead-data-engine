// Runs in the Sales Navigator results page. DOM work only — no cross-origin
// fetch happens here (that's the background service worker's job).

(() => {
  const BTN_ID = "lde-grab-btn"; // intentionally plain; nothing scraper-obvious
  const FULL_PAGE = 25; // a full Sales Nav results page
  // Title placeholder when the card shows a DIFFERENT company's role than the
  // target — the person is at the target (that's why they matched the current-
  // company filter), but the card exposes another of their concurrent roles.
  const TITLE_UNKNOWN = "(title unknown — multiple roles)";

  const norm = (s) => (s || "").replace(/\s+/g, " ").trim().toLowerCase();

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const jitter = (lo, hi) => lo + Math.random() * (hi - lo);

  // ---- extraction -----------------------------------------------------------

  // Each lead card is anchored by a person-name node; climb to the card and
  // read title/company from sibling nodes. data-anonymize attrs are the most
  // durable anchors Sales Nav exposes.
  function extractCards() {
    const nameNodes = document.querySelectorAll('[data-anonymize="person-name"]');
    const cards = [];
    nameNodes.forEach((nameEl) => {
      const card = nameEl.closest("li") || nameEl.parentElement;
      if (!card) return;
      const titleEl = card.querySelector('[data-anonymize="title"]');
      const companyEl = card.querySelector('[data-anonymize="company-name"]');
      const name = (nameEl.textContent || "").trim();
      if (!name) return;
      cards.push({
        name,
        title: (titleEl?.textContent || "").trim(),
        companyPerCard: (companyEl?.textContent || "").trim(),
      });
    });
    return cards;
  }

  // Canonical company = the "Current company" filter value. Try the filter chip
  // first; fall back to the most common per-card company (the filtered company
  // is the majority; subsidiaries/variants are the minority).
  function canonicalCompany(cards) {
    const chip = readFilterCompany();
    if (chip) return chip;
    const freq = {};
    cards.forEach((c) => {
      if (c.companyPerCard) freq[c.companyPerCard] = (freq[c.companyPerCard] || 0) + 1;
    });
    return Object.entries(freq).sort((a, b) => b[1] - a[1])[0]?.[0] || "";
  }

  function readFilterCompany() {
    // The selected "Current company" value renders as a filter pill. Find the
    // section labelled "Current company" and read its selected entry.
    const labels = [...document.querySelectorAll("*")].filter(
      (el) => el.children.length === 0 && el.textContent.trim() === "Current company"
    );
    for (const label of labels) {
      const section = label.closest("fieldset, section, div");
      const pill = section?.querySelector(
        'button[aria-label*="Remove"], li [aria-label*="Remove"]'
      );
      if (pill) {
        const txt = (pill.getAttribute("aria-label") || pill.textContent || "")
          .replace(/^Remove/i, "")
          .trim();
        if (txt) return txt;
      }
    }
    return "";
  }

  // ---- auto-scroll ----------------------------------------------------------

  // Sales Nav lazy-loads inside an inner scrollable container, not the window.
  function findScrollContainer() {
    const anyName = document.querySelector('[data-anonymize="person-name"]');
    let el = anyName?.closest("li")?.parentElement;
    while (el && el !== document.body) {
      const style = getComputedStyle(el);
      if (/(auto|scroll)/.test(style.overflowY) && el.scrollHeight > el.clientHeight) {
        return el;
      }
      el = el.parentElement;
    }
    return document.scrollingElement || document.documentElement;
  }

  // A single flick: glide `distance` px (signed) with an ease-out curve — fast
  // start, decelerating to rest, like releasing a swipe. Clamped to bounds.
  function flick(container, distance, duration) {
    return new Promise((resolve) => {
      const start = container.scrollTop;
      const max = container.scrollHeight - container.clientHeight;
      const easeOut = (t) => 1 - Math.pow(1 - t, 3);
      const t0 = performance.now();
      const step = (now) => {
        const p = Math.min((now - t0) / duration, 1);
        container.scrollTop = Math.max(0, Math.min(start + distance * easeOut(p), max));
        if (p < 1) requestAnimationFrame(step);
        else resolve();
      };
      requestAnimationFrame(step);
    });
  }

  async function autoScroll() {
    const container = findScrollContainer();
    const countCards = () =>
      document.querySelectorAll('[data-anonymize="person-name"]').length;

    let last = 0;
    let stableRounds = 0;
    const deadline = performance.now() + 90000; // hard safety cap (90s)

    // Start at the top, like a person resetting the list before reading down.
    // Flick upward in a few strokes rather than snapping to 0.
    while (container.scrollTop > 4 && performance.now() < deadline) {
      await flick(container, -container.clientHeight * jitter(1.3, 2.2), jitter(300, 550));
      await sleep(jitter(200, 500));
    }
    await sleep(jitter(300, 700)); // brief settle at the top before reading down

    // Flick-based, like a real person: a downward swipe, a pause to read, repeat
    // — occasionally a small scroll back up. Varied flick strength and pauses.
    // The read-pauses double as lazy-load time. Stop when we're at the bottom
    // and no new cards have appeared across a couple of flicks.

    while (performance.now() < deadline) {
      const vh = container.clientHeight;

      // big downward flick of varied strength
      await flick(container, vh * jitter(1.0, 1.8), jitter(350, 600));
      // read-pause between flicks (also lets cards lazy-load)
      await sleep(jitter(500, 1400));

      const count = countCards();
      const atBottom =
        container.scrollTop + container.clientHeight >= container.scrollHeight - 4;
      if (count === last && atBottom) stableRounds++;
      else stableRounds = 0;
      last = count;
      if (atBottom && stableRounds >= 2) break;
    }
  }

  // ---- pagination -----------------------------------------------------------

  // Click the "Next" pagination button so the human lands on the next page
  // ready to grab again. Returns false if there's no next page (button gone
  // or disabled). The button is at the bottom, so it must be in view first.
  function goToNextPage() {
    const btn =
      document.querySelector('button[aria-label="Next"]') ||
      [...document.querySelectorAll("button")].find(
        (b) => b.textContent.trim() === "Next"
      );
    if (!btn || btn.disabled || btn.getAttribute("aria-disabled") === "true") {
      return false;
    }
    btn.scrollIntoView({ block: "center" });
    btn.click();
    return true;
  }

  // ---- UI -------------------------------------------------------------------

  function toast(text, kind) {
    let el = document.getElementById("lde-toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "lde-toast";
      el.style.cssText =
        "position:fixed;bottom:70px;right:16px;z-index:99999;max-width:320px;" +
        "padding:10px 14px;border-radius:8px;font:13px/1.4 system-ui;" +
        "box-shadow:0 2px 10px rgba(0,0,0,.2);white-space:pre-wrap;";
      document.body.appendChild(el);
    }
    el.style.background = kind === "err" ? "#b3261e" : kind === "warn" ? "#8a6d00" : "#0b6b3a";
    el.style.color = "#fff";
    el.textContent = text;
    clearTimeout(el._t);
    el._t = setTimeout(() => el.remove(), 6000);
  }

  async function grab(btn) {
    btn.disabled = true;
    btn.textContent = "Scrolling…";
    try {
      await autoScroll();
      const cards = extractCards();
      if (!cards.length) {
        toast("No lead cards found. Is this a Sales Nav results page?", "err");
        return;
      }
      const company = canonicalCompany(cards);
      if (!company) {
        toast("Could not determine the company for this page.", "err");
        return;
      }

      // A person can hold several current roles; the card may show a role at a
      // company OTHER than the target. Keep the person (they're at the target),
      // but flag the title as unknown rather than storing the wrong role.
      let flagged = 0;
      const contacts = cards.map((c) => {
        const onTarget = c.companyPerCard && norm(c.companyPerCard) === norm(company);
        const title = onTarget ? c.title : TITLE_UNKNOWN;
        if (!onTarget) flagged++;
        return { company, name: c.name, title };
      });

      // Sanity check — surface partial/failed extraction (not the flagged ones,
      // which are expected).
      if (cards.length < FULL_PAGE - 5) {
        toast(`Only ${cards.length} cards extracted (expected ~${FULL_PAGE}). Selectors may have changed.`, "warn");
      }
      btn.textContent = "Saving…";
      // If the extension was reloaded, this stale content script can't reach it.
      if (!chrome.runtime?.id) {
        toast("Extension was reloaded — refresh this page (Cmd+R), then grab again.", "warn");
        return;
      }
      chrome.runtime.sendMessage({ type: "contacts", contacts }, (resp) => {
        if (chrome.runtime.lastError) {
          toast("Extension context lost — refresh this page (Cmd+R), then grab again.", "warn");
          return;
        }
        if (!resp?.ok) {
          const why = resp?.error
            ? "Is the local server running? (python scripts/serve.py)"
            : `server ${resp?.status}: ${resp?.data?.error || "error"}`;
          toast(`Save failed. ${why}`, "err");
          return;
        }
        const d = resp.data;
        const advanced = goToNextPage();
        const nextNote = advanced ? "\n→ next page" : "\n(last page)";
        const flagNote = flagged ? `\n${flagged} title(s) flagged unknown` : "";
        toast(`${company}\n+${d.added} added, ${d.skipped} skipped → ${d.target}${flagNote}${nextNote}`, "ok");
      });
    } catch (e) {
      toast(`Error: ${e}`, "err");
    } finally {
      btn.disabled = false;
      btn.textContent = "Grab page → CSV";
    }
  }

  function injectButton() {
    if (document.getElementById(BTN_ID)) return;
    const btn = document.createElement("button");
    btn.id = BTN_ID;
    btn.textContent = "Grab page → CSV";
    btn.style.cssText =
      "position:fixed;bottom:16px;right:16px;z-index:99999;padding:10px 16px;" +
      "border:none;border-radius:8px;background:#0a66c2;color:#fff;font:600 13px system-ui;" +
      "cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.25);";
    btn.addEventListener("click", () => grab(btn));
    document.body.appendChild(btn);
  }

  // The SPA re-renders on navigation; keep the button present.
  injectButton();
  new MutationObserver(() => injectButton()).observe(document.body, {
    childList: true,
    subtree: false,
  });
})();
