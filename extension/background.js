chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type !== "contacts") return false;
  fetch("http://127.0.0.1:8765/contacts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(msg.contacts),
  })
    .then(async (res) =>
      sendResponse({ ok: res.ok, status: res.status, data: await res.json().catch(() => ({})) })
    )
    .catch((err) => sendResponse({ ok: false, status: 0, error: String(err) }));
  return true;
});
