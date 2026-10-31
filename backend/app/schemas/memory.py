from datetime import datetime

from pydantic import BaseModel, Field


class MemoryBase(BaseModel):
    title: str
    url: str
    summary: str
    source_type: str = Field(default="article")
    topics: list[str] = Field(default_factory=list)


class MemoryCreate(MemoryBase):
    content: str = ""


class MemoryItem(MemoryBase):
    id: str
    content: str = ""
    created_at: datetime
    last_visited_at: datetime | None = None
    visit_count: int = 1
    enriched_at: datetime | None = None
