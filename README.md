# Personal Memory Intelligence

An AI-powered personal knowledge system that captures browser activity, stores memory items, and lets users search, explore timelines, inspect a knowledge graph, and query their saved web memory with keyword, semantic, or hybrid retrieval.

## Features

- Chrome extension popup to capture the current page
- Manual memory capture from the dashboard
- Recent memories with live refresh
- Keyword, semantic, and hybrid search modes
- Content-grounded LLM answers with cited page snippets
- D3 knowledge graph with clickable node focus
- Topic timeline view
- AI-style memory digest summary
- OpenAI embeddings-ready backend with local fallback

## Tech Stack

- Frontend: `React`, `Vite`, `D3`
- Backend: `FastAPI`, `Pydantic`
- Storage: `MongoDB`-ready repository path
- AI search: OpenAI embeddings or local fallback vectors
- Answer generation: OpenAI or Gemini over archived page content
- Extension: Chrome Extension Manifest V3

## Project Structure

- `backend/` FastAPI API for ingestion, search, graph, timeline, and summary
- `frontend/` React dashboard
- `extension/` Chrome extension popup and background capture
- `docs/` architecture notes

## Local Development

### 1. Create Environment File

```bash
cp .env.example .env
```

### 2. Start Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

### 4. Load Extension

1. Open Chrome extensions page
2. Turn on Developer Mode
3. Click `Load unpacked`
4. Select the `extension/` folder

## Docker Development

```bash
docker compose up --build
```

Services:

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8000`
- MongoDB: `mongodb://127.0.0.1:27017`

## OpenAI Search + Answer Setup

Set these values in `.env`:

```bash
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
ANSWER_PROVIDER=openai
ANSWER_MODEL=gpt-4.1-mini
OPENAI_API_KEY=your_key_here
```

Optional:

```bash
EMBEDDING_DIMENSIONS=512
```

Then restart the backend. If no key is set, embeddings fall back to the local engine and answers fall back to extractive summaries from the stored page content.

## Gemini Search + Answer Setup

Gemini embeddings use Google's `gemini-embedding-001` model.

Set these values in `.env`:

```bash
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=gemini-embedding-001
ANSWER_PROVIDER=gemini
ANSWER_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your_key_here
```

Optional:

```bash
EMBEDDING_DIMENSIONS=768
```

Then restart the backend. If both keys are absent, the app falls back to the local embedding engine.

## API Endpoints

- `GET /health`
- `GET /api/memories`
- `POST /api/memories`
- `GET /api/search?q=...&mode=keyword|semantic|hybrid`
  returns ranked results, a best-answer block, and cited snippets from archived pages
- `GET /api/graph`
- `GET /api/timeline`
- `GET /api/summary`

## Demo Checklist

- Add a memory manually from the dashboard
- Search it in `keyword`, `semantic`, and `hybrid` modes
- Ask a natural question like `what job openings were in infosys site`
- Open the timeline page and inspect topic growth
- Open the graph page and click nodes to inspect relationships
- Use the extension popup to save the current page
- Confirm the digest updates with recent memories, topics, and sources

## Current Status

This project is now a solid MVP with:

- working React frontend
- working FastAPI backend
- extension-based page capture
- summary, timeline, graph, and search flows
- content-grounded answer generation over archived page text

## Next Production Steps

- add authentication
- persist graph relationships in Neo4j
- use a managed MongoDB instance
- deploy frontend and backend separately
- add background jobs for enrichment and summarization

## Evaluation

`python eval_memory.py` replays a small hand-labelled set (16 pages, 24 natural-language queries, one correct page each)
through the real FastAPI routes with an in-memory MongoDB mock, so no database or API key is needed.

```
pip install -r backend/requirements.txt mongomock
python eval_memory.py
```

Measured with the local hash embedding engine (no `OPENAI_API_KEY`):

| Mode | Top-1 | Recall@5 | MRR |
|---|---|---|---|
| Keyword | 67% | 79% | 0.74 |
| Semantic | 54% | 79% | 0.65 |
| **Hybrid** | **79%** | **83%** | **0.82** |

Multi-turn: saying "open the first one again" kept the correct result in 22 of 24 two-turn dialogues.

This is a small self-built test set, not a production benchmark. Set `OPENAI_API_KEY` and rerun to measure OpenAI embeddings;
the `embedding engine:` line in the output shows which engine was used.
