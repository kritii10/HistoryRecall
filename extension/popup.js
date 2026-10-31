const saveButton = document.getElementById("saveButton");
const statusText = document.getElementById("statusText");
const pageTitle = document.getElementById("pageTitle");
const autoCaptureToggle = document.getElementById("autoCaptureToggle");
const blockDomainButton = document.getElementById("blockDomainButton");
const blockedDomains = document.getElementById("blockedDomains");

function renderBlockedDomains(domains) {
  blockedDomains.textContent = domains?.length
    ? `Blocked: ${domains.join(", ")}`
    : "No blocked domains.";
}

chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  const [tab] = tabs;
  pageTitle.textContent = tab?.title || "No active tab found.";
});

chrome.runtime.sendMessage({ type: "GET_AUTO_CAPTURE_STATE" }, (response) => {
  autoCaptureToggle.checked = Boolean(response?.enabled);
});

chrome.runtime.sendMessage({ type: "GET_BLOCKED_DOMAINS" }, (response) => {
  renderBlockedDomains(response?.blockedDomains || []);
});

autoCaptureToggle.addEventListener("change", () => {
  chrome.runtime.sendMessage(
    { type: "SET_AUTO_CAPTURE_STATE", enabled: autoCaptureToggle.checked },
    (response) => {
      if (!response?.ok) {
        statusText.textContent = "Could not update auto capture.";
        statusText.classList.add("error");
        return;
      }

      statusText.textContent = autoCaptureToggle.checked
        ? "Auto capture is on."
        : "Auto capture is off.";
      statusText.classList.remove("error");
    }
  );
});

blockDomainButton.addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "BLOCK_ACTIVE_DOMAIN" }, (response) => {
    if (!response?.ok) {
      statusText.textContent = response?.error || "Could not block domain.";
      statusText.classList.add("error");
      return;
    }

    renderBlockedDomains(response.blockedDomains);
    statusText.textContent = `Blocked ${response.domain}.`;
    statusText.classList.remove("error");
  });
});

saveButton.addEventListener("click", () => {
  saveButton.disabled = true;
  statusText.textContent = "Saving page...";
  statusText.classList.remove("error");

  chrome.runtime.sendMessage({ type: "SAVE_ACTIVE_TAB" }, (response) => {
    if (chrome.runtime.lastError || !response?.ok) {
      statusText.textContent = response?.error || "Save failed.";
      statusText.classList.add("error");
      saveButton.disabled = false;
      return;
    }

    statusText.textContent = "Saved successfully.";
    statusText.classList.remove("error");
    pageTitle.textContent = response.payload.title;
    saveButton.disabled = false;
  });
});
