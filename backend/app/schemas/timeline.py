from pydantic import BaseModel


class TimelinePoint(BaseModel):
    month: str
    topic: str
    count: int


class TimelineResponse(BaseModel):
    points: list[TimelinePoint]
