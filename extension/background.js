const API_BASE = "http://127.0.0.1:8000";
const AUTO_CAPTURE_KEY = "autoCaptureEnabled";
const LAST_CAPTURE_KEY = "lastCapturedUrls";
const BLOCKED_DOMAINS_KEY = "blockedDomains";
const CAPTURE_COOLDOWN_MS = 45_000;

function inferTopics(text) {
  const candidates = [
    "AI",
    "FastAPI",
    "Python",
    "React",
    "Graph",
    "Search",
    "LangChain",
    "MongoDB",
    "Neo4j",
    "JavaScript"
  ];
  const lowered = text.toLowerCase();
  return candidates.filter((topic) => lowered.includes(topic.toLowerCase())).slice(0, 5);
}

function isTrackableUrl(url) {
  if (!url) {
    return false;
  }

  return /^https?:\/\//.test(url);
}

function getDomain(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch (error) {
    return "";
  }
}

async function getBlockedDomains() {
  const stored = await chrome.storage.local.get(BLOCKED_DOMAINS_KEY);
  return stored[BLOCKED_DOMAINS_KEY] || [];
}

async function isBlockedDomain(url) {
  const domain = getDomain(url);
  const blockedDomains = await getBlockedDomains();
  return blockedDomains.some((blockedDomain) => domain === blockedDomain || domain.endsWith(`.${blockedDomain}`));
}

async function blockDomain(url) {
  const domain = getDomain(url);
  if (!domain) {
    return { ok: false, error: "No domain found." };
  }

  const blockedDomains = await getBlockedDomains();
  if (!blockedDomains.includes(domain)) {
    blockedDomains.push(domain);
    await chrome.storage.local.set({ [BLOCKED_DOMAINS_KEY]: blockedDomains });
  }
  return { ok: true, domain, blockedDomains };
}

async function getAutoCaptureEnabled() {
  const stored = await chrome.storage.local.get(AUTO_CAPTURE_KEY);
  if (typeof stored[AUTO_CAPTURE_KEY] === "boolean") {
    return stored[AUTO_CAPTURE_KEY];
  }
  await chrome.storage.local.set({ [AUTO_CAPTURE_KEY]: true });
  return true;
}

async function rememberCapture(url) {
  const stored = await chrome.storage.local.get(LAST_CAPTURE_KEY);
  const current = stored[LAST_CAPTURE_KEY] || {};
  current[url] = Date.now();

  const trimmed = Object.fromEntries(
    Object.entries(current)
      .filter(([, timestamp]) => Date.now() - timestamp < CAPTURE_COOLDOWN_MS)
      .slice(-50)
  );

  await chrome.storage.local.set({ [LAST_CAPTURE_KEY]: trimmed });
}

async function wasCapturedRecently(url) {
  const stored = await chrome.storage.local.get(LAST_CAPTURE_KEY);
  const current = stored[LAST_CAPTURE_KEY] || {};
  const timestamp = current[url];
  return typeof timestamp === "number" && Date.now() - timestamp < CAPTURE_COOLDOWN_MS;
}

async function buildPayload(tab) {
  const [{ result }] = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: (topics) => {
      const text = document.body.innerText;
      const foundTopics = topics.filter((topic) => text.toLowerCase().includes(topic.toLowerCase()));
      return {
        title: document.title,
        url: window.location.href,
        summary: text.slice(0, 280),
        content: text.slice(0, 5000),
        source_type: "webpage",
        topics: foundTopics
      };
    },
    args: [[
      "AI",
      "FastAPI",
      "Python",
      "React",
      "Graph",
      "Search",
      "LangChain",
      "MongoDB",
      "Neo4j",
      "JavaScript"
    ]]
  });

  const payload = {
    ...result,
    topics: result.topics.length ? result.topics : inferTopics(`${result.title} ${result.summary}`)
  };
  return payload;
}

async function saveCurrentTab(tab) {
  if (!tab.id || !tab.url || !isTrackableUrl(tab.url) || (await isBlockedDomain(tab.url))) {
    throw new Error("Missing active tab");
  }

  const payload = await buildPayload(tab);
  try {
    const response = await fetch(`${API_BASE}/api/memories`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error("Save failed");
    }

    await chrome.action.setBadgeText({ tabId: tab.id, text: "OK" });
    await chrome.action.setBadgeBackgroundColor({ tabId: tab.id, color: "#2d6b2f" });
    await rememberCapture(tab.url);
    return { ok: true, payload };
  } catch (error) {
    await chrome.action.setBadgeText({ tabId: tab.id, text: "ERR" });
    await chrome.action.setBadgeBackgroundColor({ tabId: tab.id, color: "#a32020" });
    return { ok: false, error: "Could not save page." };
  }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "SAVE_ACTIVE_TAB") {
    if (message.type === "GET_AUTO_CAPTURE_STATE") {
      getAutoCaptureEnabled().then((enabled) => sendResponse({ enabled }));
      return true;
    }

    if (message.type === "SET_AUTO_CAPTURE_STATE") {
      chrome.storage.local.set({ [AUTO_CAPTURE_KEY]: Boolean(message.enabled) }).then(() => {
        sendResponse({ ok: true, enabled: Boolean(message.enabled) });
      });
      return true;
    }

    if (message.type === "GET_BLOCKED_DOMAINS") {
      getBlockedDomains().then((blockedDomains) => sendResponse({ blockedDomains }));
      return true;
    }

    if (message.type === "BLOCK_ACTIVE_DOMAIN") {
      chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
        const [tab] = tabs;
        const result = await blockDomain(tab?.url);
        sendResponse(result);
      });
      return true;
    }

    return false;
  }

  chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
    const [tab] = tabs;
    const result = await saveCurrentTab(tab);
    sendResponse(result);
  });

  return true;
});

chrome.webNavigation.onCompleted.addListener(async ({ tabId, frameId, url }) => {
  if (frameId !== 0 || !isTrackableUrl(url)) {
    return;
  }

  const enabled = await getAutoCaptureEnabled();
  if (!enabled || (await isBlockedDomain(url)) || (await wasCapturedRecently(url))) {
    return;
  }

  try {
    const tab = await chrome.tabs.get(tabId);
    await saveCurrentTab(tab);
  } catch (error) {
    await chrome.action.setBadgeText({ tabId, text: "ERR" });
    await chrome.action.setBadgeBackgroundColor({ tabId, color: "#a32020" });
  }
});

chrome.action.onClicked.addListener(async (tab) => {
  if (!tab) {
    return;
  }
  await saveCurrentTab(tab);
});
