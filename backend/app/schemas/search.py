from pydantic import BaseModel

from app.schemas.memory import MemoryItem


class SearchAnswer(BaseModel):
    headline: str
    summary: str
    exact_url: str
    match_reason: str
    key_points: list[str] = []


class SearchCitation(BaseModel):
    title: str
    url: str
    snippet: str
    source_type: str
    relevance: str
    memory_id: str | None = None


class SearchResultItem(BaseModel):
    memory: MemoryItem
    score: float
    reason: str


class SearchResponse(BaseModel):
    query: str
    resolved_query: str
    mode: str
    engine: str
    applied_time_range: str
    conversation_id: str
    total: int
    answer: SearchAnswer | None = None
    citations: list[SearchCitation] = []
    follow_up_suggestions: list[str] = []
    items: list[SearchResultItem]
