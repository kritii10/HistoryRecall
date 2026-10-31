from pydantic import BaseModel


class SummaryResponse(BaseModel):
    total_memories: int
    top_topics: list[str]
    top_sources: list[str]
    digest: str
