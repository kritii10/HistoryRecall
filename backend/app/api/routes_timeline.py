from fastapi import APIRouter

from app.schemas.timeline import TimelineResponse
from app.services.memory_service import memory_service

router = APIRouter(prefix="/api/timeline", tags=["timeline"])


@router.get("", response_model=TimelineResponse)
def get_timeline() -> TimelineResponse:
    return memory_service.timeline()
