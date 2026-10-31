from fastapi import APIRouter, Query

from app.schemas.search import SearchResponse
from app.services.memory_service import memory_service

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search_memories(
    q: str = Query(default=""),
    mode: str = Query(default="keyword"),
    time_range: str = Query(default="all"),
    source_type: str = Query(default="all"),
    sort_by: str = Query(default="relevance"),
    conversation_id: str | None = Query(default=None),
) -> SearchResponse:
    return memory_service.search(q, mode, time_range, source_type, sort_by, conversation_id)
