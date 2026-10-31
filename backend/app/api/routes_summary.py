from fastapi import APIRouter

from app.schemas.summary import SummaryResponse
from app.services.memory_service import memory_service

router = APIRouter(prefix="/api/summary", tags=["summary"])


@router.get("", response_model=SummaryResponse)
def get_summary() -> SummaryResponse:
    return memory_service.summary()
