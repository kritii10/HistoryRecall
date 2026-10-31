from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from bson import ObjectId
from pymongo.errors import PyMongoError

from app.db.mongo import get_memory_collection
from app.schemas.memory import MemoryCreate, MemoryItem


def _serialize(document: dict[str, Any]) -> MemoryItem:
    return MemoryItem(
        id=str(document["_id"]),
        title=document["title"],
        url=document["url"],
        summary=document["summary"],
        source_type=document.get("source_type", "article"),
        topics=document.get("topics", []),
        content=document.get("content", ""),
        created_at=document["created_at"],
        last_visited_at=document.get("last_visited_at"),
        visit_count=document.get("visit_count", 1),
        enriched_at=document.get("enriched_at"),
    )


class MemoryRepository:
    def list_memories(self) -> list[MemoryItem]:
        collection = get_memory_collection()
        documents = collection.find().sort("created_at", -1)
        return [_serialize(document) for document in documents]

    def create_memory(self, payload: MemoryCreate) -> MemoryItem:
        collection = get_memory_collection()
        now = datetime.now(UTC)
        normalized_url = self._normalize_url(payload.url)
        existing = collection.find_one({"normalized_url": normalized_url})

        if existing:
            collection.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "title": payload.title or existing["title"],
                        "url": payload.url,
                        "summary": payload.summary or existing["summary"],
                        "source_type": payload.source_type,
                        "topics": payload.topics or existing.get("topics", []),
                        "content": payload.content,
                        "last_visited_at": now,
                    },
                    "$inc": {"visit_count": 1},
                },
            )
            updated = collection.find_one({"_id": existing["_id"]})
            return _serialize(updated)

        document = {
            "title": payload.title,
            "url": payload.url,
            "normalized_url": normalized_url,
            "summary": payload.summary,
            "source_type": payload.source_type,
            "topics": payload.topics,
            "content": payload.content,
            "created_at": now,
            "last_visited_at": now,
            "visit_count": 1,
        }
        result = collection.insert_one(document)
        document["_id"] = result.inserted_id
        return _serialize(document)

    def available(self) -> bool:
        try:
            get_memory_collection().database.client.admin.command("ping")
            return True
        except PyMongoError:
            return False

    def update_memory_fields(self, memory_id: str, fields: dict[str, Any]) -> MemoryItem | None:
        collection = get_memory_collection()
        collection.update_one({"_id": ObjectId(memory_id)}, {"$set": fields})
        updated = collection.find_one({"_id": ObjectId(memory_id)})
        if not updated:
            return None
        return _serialize(updated)

    def delete_memory(self, memory_id: str) -> bool:
        collection = get_memory_collection()
        result = collection.delete_one({"_id": ObjectId(memory_id)})
        return result.deleted_count > 0

    def clear_memories(self) -> int:
        collection = get_memory_collection()
        result = collection.delete_many({})
        return result.deleted_count

    @staticmethod
    def _normalize_url(url: str) -> str:
        parsed = urlsplit(url.strip())
        path = parsed.path.rstrip("/") or "/"
        return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, "", ""))
