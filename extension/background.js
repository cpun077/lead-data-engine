// Service worker: the only place that talks to the local server.
// Fetching from the extension context (with host_permissions) bypasses page
// CORS and Private Network Access checks, so the server needs no CORS handling.

const ENDPOINT = "http://127.0.0.1:8765/contacts";

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type !== "contacts") return false;

  fetch(ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(msg.contacts),
  })
    .then(async (res) => {
      const data = await res.json().catch(() => ({}));
      sendResponse({ ok: res.ok, status: res.status, data });
    })
    .catch((err) => {
      // Most common cause: the local server isn't running.
      sendResponse({ ok: false, status: 0, error: String(err) });
    });

  return true; // keep the message channel open for the async sendResponse
});
