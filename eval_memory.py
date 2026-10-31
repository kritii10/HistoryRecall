"""
Evaluate the restored HistoryRecall (Personal Memory Intelligence) backend end-to-end through its real
FastAPI routes, on a labelled set. MongoDB is mocked in-memory, so nothing touches your real data.

Run from the repo root:
    pip install fastapi pymongo pydantic httpx mongomock
    python eval_memory.py                      # embedding engine = local hash (no key needed)
    OPENAI_API_KEY=sk-... python eval_memory.py  # engine = OpenAI embeddings (use THESE numbers for "semantic")
The printed 'engine' line tells you which one you measured.
"""
import sys, time, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))
import mongomock
import app.repositories.memory_repository as repo
_COL = mongomock.MongoClient().db["memory_items"]
repo.get_memory_collection = lambda: _COL
from fastapi.testclient import TestClient
from app.main import app

PAGES = [
 ("Managing state in React apps", "React components share data through props, context and hooks like useState and useReducer. Libraries such as Redux centralise application state so that many components can read and update it predictably."),
 ("Docker container networking explained", "Docker creates bridge networks so containers can talk to each other by name. Published ports map a container port to the host, and compose files define shared networks for multi-service apps."),
 ("Python asyncio for concurrent code", "Asyncio runs many I/O-bound tasks on a single thread using async and await. The event loop switches between coroutines while they wait for network or disk responses."),
 ("PostgreSQL index tuning", "B-tree indexes speed up lookups and range queries in PostgreSQL. Use EXPLAIN ANALYZE to see whether a query uses an index scan or a slow sequential scan."),
 ("Baking sourdough bread at home", "A sourdough starter is a fermented mix of flour and water full of wild yeast. Feed it regularly, mix the dough, let it rise slowly overnight and bake in a hot Dutch oven."),
 ("Beginner marathon training plan", "Build weekly mileage gradually with easy runs and one long run each week. Include rest days, a taper in the last two weeks and practice fuelling with gels."),
 ("Kubernetes pods and deployments", "A pod is the smallest deployable unit in Kubernetes and wraps one or more containers. Deployments manage replicas, rolling updates and self-healing for those pods."),
 ("How transformers use attention", "Transformer models use self-attention to weigh how relevant each token is to every other token. Stacked attention layers and positional encodings let them model long sequences in language tasks."),
 ("Two weeks in Japan on a budget", "Use a rail pass, stay in hostels or business hotels and eat at convenience stores and ramen counters. Visit Tokyo, Kyoto and Osaka and travel in spring or autumn for good weather."),
 ("Git rebase versus merge", "Merge keeps full history with a merge commit while rebase rewrites commits onto a new base for a linear history. Never rebase branches that others have already pulled."),
 ("CSS flexbox and grid layouts", "Flexbox arranges items along one axis and is ideal for navbars and rows. CSS grid controls rows and columns together for full page layouts and responsive designs."),
 ("Bodyweight workout with no equipment", "Squats, push-ups, lunges and planks build strength at home without gym machines. Do three sets of each exercise and rest briefly between sets."),
 ("Mutual funds and SIP investing", "A systematic investment plan puts a fixed amount into a mutual fund every month. Rupee cost averaging and long horizons help smooth out market volatility."),
 ("JWT authentication in FastAPI", "Issue a signed JSON Web Token after login and verify it with a dependency on protected routes. Store a short expiry and refresh tokens to keep sessions secure."),
 ("Sleep hygiene tips for better rest", "Keep a consistent bedtime, avoid caffeine late in the day and dim screens before sleeping. A cool dark room improves sleep quality and mood."),
 ("Photography exposure triangle", "Aperture, shutter speed and ISO together control how bright a photo is. A wide aperture blurs the background, a fast shutter freezes motion and high ISO adds noise."),
]

QUERIES = [  # (vague natural-language query, index of the page the user means)
 ("that article about sharing data between components in a javascript UI library", 0),
 ("redux or hooks for keeping app data in sync", 0),
 ("how containers on the same host communicate with each other", 1),
 ("running many tasks at once in python without threads", 2),
 ("making a slow database query faster with lookups", 3),
 ("how to find out if my sql query is scanning the whole table", 3),
 ("making bread with wild yeast", 4),
 ("how to prepare for running a 42 km race", 5),
 ("orchestrating containers across a cluster with auto-scaling", 6),
 ("why do language models pay attention to different words", 7),
 ("backpacking trip plan for tokyo and kyoto cheaply", 8),
 ("should i squash commits or keep history when combining branches", 9),
 ("rewriting commit history safely", 9),
 ("laying out a web page in rows and columns", 10),
 ("exercises i can do in my room to get fit", 11),
 ("investing a small fixed amount every month in the market", 12),
 ("secure login tokens for my python api", 13),
 ("falling asleep earlier and waking up refreshed", 14),
 ("why is my camera image too dark or too blurry", 15),
 ("what is the smallest unit you can deploy in k8s", 6),
 ("hands-free way to stay fit with only my own weight", 11),
 ("stop the page from jumping around on mobile with a one-dimensional layout", 10),
 ("keeping tokens short-lived for web security", 13),
 ("long run and rest days before a race", 5),
]

def main():
    c = TestClient(app)
    for i, (title, body) in enumerate(PAGES):
        r = c.post("/api/memories", json={"title": title, "url": f"https://example.com/p{i}",
                   "content": body, "summary": body[:80], "source_type": "article", "topics": []})
        assert r.status_code == 201, r.text
    title_to_idx = {t: i for i, (t, _) in enumerate(PAGES)}
    engine = None
    print(f"Pages: {len(PAGES)} | Queries: {len(QUERIES)}")
    for mode in ("keyword", "semantic", "hybrid"):
        h1 = h5 = 0; rr = 0.0; ms = []
        for q, target in QUERIES:
            t = time.perf_counter()
            res = c.get("/api/search", params={"q": q, "mode": mode}).json()
            ms.append((time.perf_counter() - t) * 1000)
            engine = res.get("engine")
            ranked = [title_to_idx.get(it.get("memory", it).get("title")) for it in res["items"]]
            rank = ranked.index(target) + 1 if target in ranked else None
            h1 += rank == 1; h5 += bool(rank and rank <= 5); rr += (1 / rank) if rank else 0
        n = len(QUERIES)
        print(f"{mode:>8}: top-1 {h1/n:4.0%} ({h1}/{n}) | recall@5 {h5/n:4.0%} | MRR {rr/n:.2f} | avg latency {sum(ms)/n:5.1f} ms")
    print(f"embedding engine: {engine}")
    # multi-turn: turn 2 'the first one again' should keep pointing at turn 1's top result
    ok = tot = 0
    for q, _ in QUERIES:
        r1 = c.get("/api/search", params={"q": q, "mode": "hybrid"}).json()
        if not r1["items"]: continue
        top1 = r1["items"][0].get("memory", r1["items"][0]).get("title")
        r2 = c.get("/api/search", params={"q": "open the first one again", "mode": "hybrid",
                                          "conversation_id": r1["conversation_id"]}).json()
        tot += 1
        ok += bool(r2["items"]) and r2["items"][0].get("memory", r2["items"][0]).get("title") == top1
    print(f"multi-turn follow-up ('the first one again') keeps turn-1 top result: {ok}/{tot} = {ok/max(tot,1):.0%}")

if __name__ == "__main__":
    main()
