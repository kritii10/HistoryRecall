from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    label: str
    type: str


class GraphLink(BaseModel):
    source: str
    target: str
    label: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]
