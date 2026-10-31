from pymongo import MongoClient
from pymongo.collection import Collection

from app.core.config import settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=1500)
    return _client


def get_memory_collection() -> Collection:
    database = get_client().get_default_database()
    return database["memory_items"]
