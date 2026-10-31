import os
from pathlib import Path

from pydantic import BaseModel
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "backend" / ".env")


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "Personal Memory Intelligence API")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    mongo_url: str = os.getenv("MONGO_URL", "mongodb://localhost:27017/ai_memory_graph")
    neo4j_url: str = os.getenv("NEO4J_URL", "bolt://localhost:7687")
    vector_db_url: str = os.getenv("VECTOR_DB_URL", "http://localhost:8080")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "auto")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    embedding_dimensions: int = int(os.getenv("EMBEDDING_DIMENSIONS", "0"))
    answer_provider: str = os.getenv("ANSWER_PROVIDER", "auto")
    answer_model: str = os.getenv("ANSWER_MODEL", "gpt-4.1-mini")


settings = Settings()
