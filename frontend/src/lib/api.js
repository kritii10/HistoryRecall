const API_BASE = "http://127.0.0.1:8000";

async function request(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function send(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function remove(path) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "DELETE"
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

export function searchMemories(
  query,
  mode = "keyword",
  timeRange = "all",
  sourceType = "all",
  sortBy = "relevance",
  conversationId = ""
) {
  return request(
    `/api/search?q=${encodeURIComponent(query)}&mode=${encodeURIComponent(mode)}&time_range=${encodeURIComponent(timeRange)}&source_type=${encodeURIComponent(sourceType)}&sort_by=${encodeURIComponent(sortBy)}&conversation_id=${encodeURIComponent(conversationId)}`
  );
}

export function createMemory(payload) {
  return send("/api/memories", payload);
}

export function fetchMemories() {
  return request("/api/memories");
}

export function fetchTimeline() {
  return request("/api/timeline");
}

export function fetchGraph() {
  return request("/api/graph");
}

export function fetchSummary() {
  return request("/api/summary");
}

export function deleteMemory(id) {
  return remove(`/api/memories/${id}`);
}

export function clearMemories() {
  return remove("/api/memories");
}

export function exportMemories() {
  return request("/api/memories/export");
}

export function importMemories(payload) {
  return send("/api/memories/import", payload);
}
