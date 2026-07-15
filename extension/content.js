(() => {
  const FULL_PAGE = 25;
  const TITLE_UNKNOWN = "(title unknown — multiple roles)";
  const norm = (s) =>
    (s || "")
      .toLowerCase()
      .replace(/&/g, " and ")
      .replace(/[.,]/g, " ")
      .replace(/\b(inc|llc|ltd|corp|incorporated|company)\b/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  const sameCompany = (a, b) => {
    a = norm(a);
    b = norm(b);
    return !!a && !!b && (a === b || a.startsWith(b + " ") || b.startsWith(a + " "));
  };
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const jitter = (lo, hi) => lo + Math.random() * (hi - lo);

  function cardCompany(card, titleEl) {
    const linked = card.querySelector('[data-anonymize="company-name"]');
    if (linked?.textContent.trim()) return linked.textContent.trim();
    const subtitle =
      titleEl?.closest(".artdeco-entity-lockup__subtitle") || titleEl?.parentElement;
    if (!subtitle) return "";
    let txt = subtitle.textContent || "";
    if (titleEl) txt = txt.replace(titleEl.textContent, " ");
    return txt.replace(/·/g, " ").replace(/\s+/g, " ").trim();
  }

  function extractCards() {
    const cards = [];
    document.querySelectorAll('[data-anonymize="person-name"]').forEach((nameEl) => {
      const card = nameEl.closest("li") || nameEl.parentElement;
      const name = (nameEl.textContent || "").trim();
      if (!card || !name) return;
      const titleEl = card.querySelector('[data-anonymize="title"]');
      cards.push({
        name,
        title: (titleEl?.textContent || "").trim(),
        companyPerCard: cardCompany(card, titleEl),
      });
    });
    return cards;
  }

  function readFilterCompany() {
    const labels = [...document.querySelectorAll("*")].filter(
      (el) => el.children.length === 0 && el.textContent.trim() === "Current company"
    );
    for (const label of labels) {
      const pill = label
        .closest("fieldset, section, div")
        ?.querySelector('button[aria-label*="Remove"], li [aria-label*="Remove"]');
      const txt = (pill?.getAttribute("aria-label") || pill?.textContent || "")
        .replace(/^Remove/i, "")
        .trim();
      if (txt) return txt;
    }
    return "";
  }

  function findScrollContainer() {
    let el = document.querySelector('[data-anonymize="person-name"]')?.closest("li")?.parentElement;
    while (el && el !== document.body) {
      const { overflowY } = getComputedStyle(el);
      if (/(auto|scroll)/.test(overflowY) && el.scrollHeight > el.clientHeight) return el;
      el = el.parentElement;
    }
    return document.scrollingElement || document.documentElement;
  }

  function flick(container, distance, duration) {
    return new Promise((resolve) => {
      const start = container.scrollTop;
      const max = container.scrollHeight - container.clientHeight;
      const ease = (t) => 1 - Math.pow(1 - t, 3);
      const t0 = performance.now();
      const step = (now) => {
        const p = Math.min((now - t0) / duration, 1);
        container.scrollTop = Math.max(0, Math.min(start + distance * ease(p), max));
        p < 1 ? requestAnimationFrame(step) : resolve();
      };
      requestAnimationFrame(step);
    });
  }

  async function autoScroll() {
    const container = findScrollContainer();
    const deadline = performance.now() + 90000;

    while (container.scrollTop > 4 && performance.now() < deadline) {
      await flick(container, -container.clientHeight * jitter(1.3, 2.2), jitter(300, 550));
      await sleep(jitter(200, 500));
    }
    await sleep(jitter(300, 700));

    while (performance.now() < deadline) {
      await flick(container, container.clientHeight * jitter(1.0, 1.8), jitter(350, 600));
      await sleep(jitter(500, 1400));
      if (container.scrollTop + container.clientHeight >= container.scrollHeight - 4) break;
    }
  }

  function goToNextPage() {
    const btn =
      document.querySelector('button[aria-label="Next"]') ||
      [...document.querySelectorAll("button")].find((b) => b.textContent.trim() === "Next");
    if (!btn || btn.disabled || btn.getAttribute("aria-disabled") === "true") return false;
    btn.scrollIntoView({ block: "center" });
    btn.click();
    return true;
  }

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
      if (!cards.length) return toast("No lead cards found. On a Sales Nav results page?", "err");

      const filterCompany = readFilterCompany();
      let flagged = 0;
      let contacts;
      if (filterCompany) {
        contacts = cards.map((c) => {
          if (sameCompany(c.companyPerCard, filterCompany))
            return { company: filterCompany, name: c.name, title: c.title };
          flagged++;
          const seen = [c.title, c.companyPerCard].filter(Boolean).join(" @ ");
          return { company: filterCompany, name: c.name,
                   title: seen ? `${TITLE_UNKNOWN}: ${seen}` : TITLE_UNKNOWN };
        });
      } else {
        contacts = cards
          .filter((c) => c.companyPerCard)
          .map((c) => ({ company: c.companyPerCard, name: c.name, title: c.title }));
      }
      if (!contacts.length) return toast("No company found for any card.", "err");
      const label = filterCompany || `${new Set(contacts.map((c) => c.company)).size} companies`;

      if (cards.length < FULL_PAGE - 5)
        toast(`Only ${cards.length} cards (expected ~${FULL_PAGE}). Selectors may have changed.`, "warn");

      btn.textContent = "Saving…";
      if (!chrome.runtime?.id)
        return toast("Extension reloaded — refresh this page (Cmd+R), then grab again.", "warn");

      chrome.runtime.sendMessage({ type: "contacts", contacts }, (resp) => {
        if (chrome.runtime.lastError)
          return toast("Extension context lost — refresh this page (Cmd+R).", "warn");
        if (!resp?.ok) {
          const why = resp?.error
            ? "Is the local server running? (python scripts/serve.py)"
            : `server ${resp?.status}: ${resp?.data?.error || "error"}`;
          return toast(`Save failed. ${why}`, "err");
        }
        const d = resp.data;
        const flagNote = flagged ? `\n${flagged} title(s) flagged unknown` : "";
        const nextNote = goToNextPage() ? "\n→ next page" : "\n(last page)";
        toast(`${label}\n+${d.added} added, ${d.skipped} skipped → ${d.target}${flagNote}${nextNote}`, "ok");
      });
    } catch (e) {
      toast(`Error: ${e}`, "err");
    } finally {
      btn.disabled = false;
      btn.textContent = "Grab page → CSV";
    }
  }

  function injectButton() {
    if (document.getElementById("lde-grab-btn")) return;
    const btn = document.createElement("button");
    btn.id = "lde-grab-btn";
    btn.textContent = "Grab page → CSV";
    btn.style.cssText =
      "position:fixed;bottom:16px;right:16px;z-index:99999;padding:10px 16px;border:none;" +
      "border-radius:8px;background:#0a66c2;color:#fff;font:600 13px system-ui;" +
      "cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.25);";
    btn.addEventListener("click", () => grab(btn));
    document.body.appendChild(btn);
  }

  injectButton();
  new MutationObserver(() => injectButton()).observe(document.body, { childList: true });
})();
