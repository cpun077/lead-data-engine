// Runs in the Sales Navigator results page. DOM work only — no cross-origin
// fetch happens here (that's the background service worker's job).

(() => {
  const BTN_ID = "lde-grab-btn"; // intentionally plain; nothing scraper-obvious
  const FULL_PAGE = 25; // a full Sales Nav results page

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

  async function autoScroll() {
    const container = findScrollContainer();
    const countCards = () =>
      document.querySelectorAll('[data-anonymize="person-name"]').length;
    let stable = 0;
    let last = 0;
    // Scroll in viewport-sized steps (not straight to the bottom) so each chunk
    // gets a chance to lazy-load, and wait long enough for it to render.
    for (let i = 0; i < 80 && stable < 5; i++) {
      const step = Math.max(300, container.clientHeight * 0.8);
      container.scrollTop = Math.min(container.scrollTop + step, container.scrollHeight);
      await sleep(jitter(1200, 1800)); // slower, jittered — give lazy-load time
      const count = countCards();
      if (count === last) stable++; // no new cards this round
      else stable = 0; // still loading — reset the patience counter
      last = count;
      // At the very bottom with no new cards for 2 rounds → done, skip the wait.
      const atBottom =
        container.scrollTop + container.clientHeight >= container.scrollHeight - 4;
      if (atBottom && stable >= 2) break;
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

      // Sanity checks — surface partial/failed extraction instead of silently
      // under-collecting.
      const missingTitle = cards.filter((c) => !c.title).length;
      if (cards.length < FULL_PAGE - 5) {
        toast(`Only ${cards.length} cards extracted (expected ~${FULL_PAGE}). Selectors may have changed.`, "warn");
      } else if (missingTitle) {
        toast(`${missingTitle}/${cards.length} cards missing a title — partial selector rot?`, "warn");
      }

      const contacts = cards.map((c) => ({ company, name: c.name, title: c.title }));
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
        toast(`${company}\n+${d.added} added, ${d.skipped} skipped → ${d.target}${nextNote}`, "ok");
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
