import { useEffect, useState } from "react";
import {
  clearMemories,
  createMemory,
  deleteMemory,
  exportMemories,
  fetchMemories,
  fetchSummary,
  importMemories,
  searchMemories
} from "../lib/api";

function highlightSegments(text, query) {
  if (!text) {
    return text;
  }

  const tokens = Array.from(
    new Set(
      query
        .toLowerCase()
        .split(/[^a-z0-9]+/i)
        .filter((token) => token.length > 2)
    )
  );

  if (!tokens.length) {
    return text;
  }

  const pattern = new RegExp(`(${tokens.map((token) => token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");
  const parts = text.split(pattern);
  return parts.map((part, index) =>
    tokens.includes(part.toLowerCase()) ? <mark key={`${part}-${index}`}>{part}</mark> : part
  );
}

function formatHost(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function HomePage() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("keyword");
  const [timeRange, setTimeRange] = useState("all");
  const [sourceType, setSourceType] = useState("all");
  const [sortBy, setSortBy] = useState("relevance");
  const [data, setData] = useState({
    total: 0,
    mode: "keyword",
    applied_time_range: "all",
    answer: null,
    citations: [],
    follow_up_suggestions: [],
    resolved_query: "",
    conversation_id: "",
    items: []
  });
  const [conversationId, setConversationId] = useState("");
  const [recentMemories, setRecentMemories] = useState([]);
  const [summary, setSummary] = useState({
    total_memories: 0,
    top_topics: [],
    top_sources: [],
    digest: ""
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);
  const [form, setForm] = useState({
    title: "",
    url: "",
    summary: "",
    topics: ""
  });

  useEffect(() => {
    let ignore = false;

    async function loadSearch() {
      try {
        setLoading(true);
        setError("");
        const result = await searchMemories(query, mode, timeRange, sourceType, sortBy, conversationId);
        if (!ignore) {
          setData(result);
          setConversationId(result.conversation_id || "");
        }
      } catch (err) {
        if (!ignore) {
          setError("Could not load memories.");
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }

    loadSearch();

    return () => {
      ignore = true;
    };
  }, [query, mode, timeRange, sourceType, sortBy]);

  useEffect(() => {
    let ignore = false;

    async function loadRecent() {
      try {
        const [items, summaryData] = await Promise.all([fetchMemories(), fetchSummary()]);
        if (!ignore) {
          setRecentMemories(items.slice(0, 5));
          setSummary(summaryData);
        }
      } catch (err) {
        if (!ignore) {
          setError("Could not load recent memories.");
        }
      }
    }

    loadRecent();
    const intervalId = window.setInterval(loadRecent, 10000);

    return () => {
      ignore = true;
      window.clearInterval(intervalId);
    };
  }, []);

  function updateForm(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value
    }));
  }

  async function refreshDashboard() {
    const [searchResult, recentItems, summaryData] = await Promise.all([
      searchMemories(query, mode, timeRange, sourceType, sortBy, conversationId),
      fetchMemories(),
      fetchSummary()
    ]);
    setData(searchResult);
    setConversationId(searchResult.conversation_id || "");
    setRecentMemories(recentItems.slice(0, 5));
    setSummary(summaryData);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setSaveMessage("");
    setError("");

    try {
      await createMemory({
        title: form.title,
        url: form.url,
        summary: form.summary,
        source_type: "manual",
        topics: form.topics
          .split(",")
          .map((topic) => topic.trim())
          .filter(Boolean),
        content: form.summary
      });

      setForm({
        title: "",
        url: "",
        summary: "",
        topics: ""
      });
      setSaveMessage("Memory saved.");
      await refreshDashboard();
    } catch (err) {
      setError("Could not save memory.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteMemory(id) {
    try {
      await deleteMemory(id);
      await refreshDashboard();
    } catch (err) {
      setError("Could not delete memory.");
    }
  }

  async function handleClearMemories() {
    if (!confirmClear) {
      setError("Please confirm clear all first.");
      return;
    }
    try {
      await clearMemories();
      setConfirmClear(false);
      await refreshDashboard();
    } catch (err) {
      setError("Could not clear memories.");
    }
  }

  async function handleExportMemories() {
    try {
      const payload = await exportMemories();
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "ai-memory-graph-export.json";
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError("Could not export memories.");
    }
  }

  async function handleImportFile(event) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      const payload = parsed.map((item) => ({
        title: item.title,
        url: item.url,
        summary: item.summary,
        source_type: item.source_type || "manual",
        topics: item.topics || [],
        content: item.summary || ""
      }));
      await importMemories(payload);
      await refreshDashboard();
      setSaveMessage("Memories imported.");
    } catch (err) {
      setError("Could not import memories.");
    } finally {
      event.target.value = "";
    }
  }

  return (
    <section className="dashboard-page">
      <div className="hero-grid">
        <div className="panel hero hero-primary">
          <div className="hero-copy">
            <p className="eyebrow">Memory Search</p>
            <h2>Ask your internet memory a simple question</h2>
            <p className="hero-text">
              Turn browsing history into a living recall system with semantic search, visit analytics,
              and connected context across time.
            </p>
          </div>
          <input
            className="search-input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder='Try "FastAPI", "Transformers", or "LangChain"'
          />
          <div className="mode-row">
            {["keyword", "semantic", "hybrid"].map((option) => (
              <button
                key={option}
                type="button"
                className={mode === option ? "mode-button active" : "mode-button"}
                onClick={() => setMode(option)}
              >
                {option}
              </button>
            ))}
          </div>
          <div className="mode-row">
            {[
              ["all", "All time"],
              ["today", "Today"],
              ["week", "This week"],
              ["month", "This month"]
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                className={timeRange === value ? "mode-button active" : "mode-button"}
                onClick={() => setTimeRange(value)}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="filter-row">
            <select className="filter-select" value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
              <option value="all">All sources</option>
              <option value="webpage">Web pages</option>
              <option value="manual">Manual</option>
              <option value="repo">Repo</option>
              <option value="article">Article</option>
              <option value="documentation">Documentation</option>
            </select>
            <select className="filter-select" value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
              <option value="relevance">Sort: Relevance</option>
              <option value="recent">Sort: Recent</option>
              <option value="visits">Sort: Visits</option>
            </select>
            <button className="secondary-dashboard-button" type="button" onClick={() => setSettingsOpen((open) => !open)}>
              {settingsOpen ? "Hide settings" : "Open settings"}
            </button>
          </div>
          <div className="suggestion-row">
            {[
              "careers viewed today",
              "infosys",
              "google searches",
              "AI webpages this week"
            ].map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                className="suggestion-chip"
                onClick={() => setQuery(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>
          <p className="muted hero-note">Results update live as you type.</p>
        </div>

        <aside className="panel hero hero-side">
          <p className="eyebrow">Memory Snapshot</p>
          <h3>Your knowledge space right now</h3>
          <div className="snapshot-stack">
            <div className="snapshot-card">
              <span className="snapshot-label">Total memories</span>
              <strong>{summary.total_memories}</strong>
            </div>
            <div className="snapshot-card">
              <span className="snapshot-label">Top topics</span>
              <strong>{summary.top_topics.join(", ") || "None yet"}</strong>
            </div>
            <div className="snapshot-card">
              <span className="snapshot-label">Top sources</span>
              <strong>{summary.top_sources.join(", ") || "None yet"}</strong>
            </div>
          </div>
          <p className="digest-text compact">{summary.digest}</p>
        </aside>
      </div>

      {settingsOpen ? (
        <div className="panel settings-panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Controls</p>
              <h3>Import, export, and protect your memory data</h3>
            </div>
          </div>
          <div className="settings-grid">
            <div className="settings-card">
              <h4>Import / Export</h4>
              <p className="muted">Take your memory data with you or restore it from a file.</p>
              <div className="action-row">
                <button className="secondary-dashboard-button" type="button" onClick={handleExportMemories}>
                  Export JSON
                </button>
                <label className="secondary-dashboard-button file-button">
                  Import JSON
                  <input type="file" accept="application/json" onChange={handleImportFile} hidden />
                </label>
              </div>
            </div>
            <div className="settings-card danger-zone">
              <h4>Danger Zone</h4>
              <p className="muted">Clear all memories only when you are sure.</p>
              <label className="confirm-row">
                <input
                  type="checkbox"
                  checked={confirmClear}
                  onChange={(event) => setConfirmClear(event.target.checked)}
                />
                <span>I understand this will remove all saved memories.</span>
              </label>
              <button className="danger-button" type="button" onClick={handleClearMemories}>
                Confirm and Clear All
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="dashboard-grid">
        <div className="panel results-panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Recall Results</p>
              <h3>Results</h3>
              <span className="muted">
                {loading ? "Loading..." : `${data.total} memories`}
              </span>
            </div>
            <div className="action-row">
              <span className="engine-pill">{data.engine || "keyword-ranker"}</span>
              <span className="engine-pill subtle">{sourceType}</span>
              <span className="engine-pill subtle">{sortBy}</span>
              <span className="engine-pill subtle">{data.applied_time_range || timeRange}</span>
            </div>
          </div>

          {error ? <p className="error">{error}</p> : null}

          {data.resolved_query && data.resolved_query !== query ? (
            <p className="resolved-query">
              Interpreted as: <strong>{data.resolved_query}</strong>
            </p>
          ) : null}

          {data.answer ? (
            <div className="answer-card">
              <p className="eyebrow">Best Answer</p>
              <h4>{data.answer.headline}</h4>
              <p>{data.answer.summary}</p>
              <a className="answer-link" href={data.answer.exact_url} target="_blank" rel="noreferrer">
                {data.answer.exact_url}
              </a>
              <p className="match-reason">{data.answer.match_reason}</p>
              {data.answer.key_points?.length ? (
                <div className="answer-points">
                  {data.answer.key_points.map((point) => (
                    <div key={point} className="answer-point">
                      {highlightSegments(point, data.resolved_query || query)}
                    </div>
                  ))}
                </div>
              ) : null}
              {data.follow_up_suggestions?.length ? (
                <div className="suggestion-row follow-up-row">
                  {data.follow_up_suggestions.map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      className="suggestion-chip follow-up-chip"
                      onClick={() => setQuery(suggestion)}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              ) : null}
              {data.citations?.length ? (
                <div className="citation-list">
                  {data.citations.map((citation) => (
                    <article key={`${citation.url}-${citation.title}`} className="citation-card">
                      <div className="citation-header">
                        <div className="citation-meta">
                          <p className="badge">{citation.source_type}</p>
                          <span className="citation-domain">{formatHost(citation.url)}</span>
                        </div>
                        <span className="citation-reason">{citation.relevance}</span>
                      </div>
                      <strong className="citation-title">{highlightSegments(citation.title, data.resolved_query || query)}</strong>
                      <p className="citation-snippet">{highlightSegments(citation.snippet, data.resolved_query || query)}</p>
                      <a className="answer-link" href={citation.url} target="_blank" rel="noreferrer">
                        {citation.url}
                      </a>
                    </article>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}

          {data.items.length === 0 && !loading ? (
            <div className="empty-state">
              <h4>No matching memories yet</h4>
              <p>
                Try a different keyword, switch to semantic or hybrid search, or save a new memory
                that contains this topic.
              </p>
            </div>
          ) : (
            <div className="card-grid">
              {data.items.map((item) => (
                <article key={item.memory.id} className="memory-card">
                  <div className="card-top-row">
                    <p className="badge">{item.memory.source_type}</p>
                    <span className="score-pill">Score {item.score}</span>
                  </div>
                  <h4>{highlightSegments(item.memory.title, data.resolved_query || query)}</h4>
                  <p>{highlightSegments(item.memory.summary, data.resolved_query || query)}</p>
                  <p className="match-reason">{item.reason}</p>
                  <p className="muted">Visits: {item.memory.visit_count}</p>
                  <p className="link-text">{highlightSegments(item.memory.url, data.resolved_query || query)}</p>
                  <button
                    className="danger-button"
                    type="button"
                    onClick={() => handleDeleteMemory(item.memory.id)}
                  >
                    Delete
                  </button>
                  <div className="topic-row">
                    {item.memory.topics.map((topic) => (
                      <span key={topic} className="topic-chip">
                        {topic}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>

        <aside className="panel insight-rail">
          <div className="section-header rail-header">
            <div>
              <p className="eyebrow">Knowledge Pulse</p>
              <h3>Signals from your browsing memory</h3>
            </div>
          </div>
          <div className="summary-grid summary-grid-rail">
            <div className="summary-card">
              <strong>{summary.total_memories}</strong>
              <span>Total memories</span>
            </div>
            <div className="summary-card">
              <strong>{summary.top_topics.join(", ") || "None yet"}</strong>
              <span>Top topics</span>
            </div>
            <div className="summary-card">
              <strong>{summary.top_sources.join(", ") || "None yet"}</strong>
              <span>Top sources</span>
            </div>
          </div>
          <p className="digest-text">{summary.digest}</p>
        </aside>
      </div>

      <div className="dashboard-grid lower-grid">
        <div className="stack-column">
          <div className="panel">
            <div className="section-header">
              <div>
                <p className="eyebrow">Manual Capture</p>
                <h3>Save something into your memory graph</h3>
              </div>
            </div>

            <form className="memory-form" onSubmit={handleSubmit}>
              <input
                className="form-input"
                value={form.title}
                onChange={(event) => updateForm("title", event.target.value)}
                placeholder="Title"
                required
              />
              <input
                className="form-input"
                value={form.url}
                onChange={(event) => updateForm("url", event.target.value)}
                placeholder="URL"
                required
              />
              <textarea
                className="form-input form-textarea"
                value={form.summary}
                onChange={(event) => updateForm("summary", event.target.value)}
                placeholder="Short summary"
                required
              />
              <input
                className="form-input"
                value={form.topics}
                onChange={(event) => updateForm("topics", event.target.value)}
                placeholder="Topics, separated by commas"
              />
              <button className="primary-button" type="submit" disabled={saving}>
                {saving ? "Saving..." : "Save Memory"}
              </button>
            </form>

            {saveMessage ? <p className="success">{saveMessage}</p> : null}
          </div>

          <div className="panel">
            <div className="section-header">
              <div>
                <p className="eyebrow">Recent Activity</p>
                <h3>Recent Memories</h3>
                <span className="muted">Newest captures stay within reach here.</span>
              </div>
            </div>

            <div className="recent-strip">
              {recentMemories.map((item) => (
                <article key={item.id} className="recent-item recent-card-horizontal">
                  <div>
                    <p className="badge">{item.source_type}</p>
                    <h4>{item.title}</h4>
                    <p className="muted">{new Date(item.created_at).toLocaleString()}</p>
                    <p className="muted">Visits: {item.visit_count}</p>
                    <button
                      className="danger-button"
                      type="button"
                      onClick={() => handleDeleteMemory(item.id)}
                    >
                      Delete
                    </button>
                  </div>
                  <div className="topic-row">
                    {item.topics.map((topic) => (
                      <span key={topic} className="topic-chip">
                        {topic}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Deep Insight</p>
              <h3>What this dashboard can answer now</h3>
              <span className="muted">Hybrid search now handles more natural question phrasing.</span>
            </div>
          </div>
          <div className="mini-list">
            {[
              '“what job openings were in infosys site”',
              '“show google searches from today”',
              '“which repo did I open about transformers”',
              '“docs I saw this week for fastapi”'
            ].map((example) => (
              <div key={example} className="list-item">
                <strong>{example}</strong>
                <span>
                  The search engine now infers time hints, site hints, and intent like jobs, repos,
                  or documentation before ranking results.
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
