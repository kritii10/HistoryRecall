from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_graph import router as graph_router
from app.api.routes_health import router as health_router
from app.api.routes_memory import router as memory_router
from app.api.routes_search import router as search_router
from app.api.routes_summary import router as summary_router
from app.api.routes_timeline import router as timeline_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend for browser memory capture, semantic search, timeline, and graph views.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(memory_router)
app.include_router(search_router)
app.include_router(graph_router)
app.include_router(timeline_router)
app.include_router(summary_router)
