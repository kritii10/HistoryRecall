from fastapi import APIRouter

from app.schemas.graph import GraphResponse
from app.services.memory_service import memory_service

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("", response_model=GraphResponse)
def get_graph() -> GraphResponse:
    return memory_service.graph()
