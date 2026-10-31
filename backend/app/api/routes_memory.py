from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.schemas.memory import MemoryCreate, MemoryItem
from app.services.memory_service import memory_service

router = APIRouter(prefix="/api/memories", tags=["memories"])


@router.get("", response_model=list[MemoryItem])
def list_memories() -> list[MemoryItem]:
    return memory_service.list_memories()


@router.get("/export", response_model=list[MemoryItem])
def export_memories() -> list[MemoryItem]:
    return memory_service.list_memories()


@router.post("/import", response_model=dict[str, int])
def import_memories(payload: list[MemoryCreate]) -> dict[str, int]:
    imported_count = memory_service.import_memories(payload)
    return {"imported_count": imported_count}


@router.post("", response_model=MemoryItem, status_code=201)
def create_memory(payload: MemoryCreate, background_tasks: BackgroundTasks) -> MemoryItem:
    memory = memory_service.create_memory(payload)
    background_tasks.add_task(memory_service.enrich_memory, memory.id)
    return memory


@router.delete("/{memory_id}")
def delete_memory(memory_id: str) -> dict[str, bool]:
    deleted = memory_service.delete_memory(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": True}


@router.delete("")
def clear_memories() -> dict[str, int]:
    deleted_count = memory_service.clear_memories()
    return {"deleted_count": deleted_count}
