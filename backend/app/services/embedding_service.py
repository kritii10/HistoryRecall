from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict

import httpx

from app.core.config import settings


class EmbeddingService:
    def __init__(self) -> None:
        self._cache: dict[str, list[float]] = {}

    def provider_name(self) -> str:
        if self._should_use_openai():
            return "openai"
        if self._should_use_gemini():
            return "gemini"
        return "local-hash"

    def embed(self, text: str) -> list[float]:
        cache_key = f"{self.provider_name()}::{text}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self._should_use_openai():
            try:
                vector = self._openai_embed(text)
                self._cache[cache_key] = vector
                return vector
            except Exception:
                pass

        if self._should_use_gemini():
            try:
                vector = self._gemini_embed(text)
                self._cache[cache_key] = vector
                return vector
            except Exception:
                pass

        vector = self._local_embed(text)
        self._cache[cache_key] = vector
        return vector

    def similarity(self, left_text: str, right_text: str) -> float:
        left = self.embed(left_text)
        right = self.embed(right_text)
        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if not left_norm or not right_norm:
            return 0.0
        return numerator / (left_norm * right_norm)

    def _should_use_openai(self) -> bool:
        if settings.embedding_provider == "openai":
            return bool(settings.openai_api_key)
        if settings.embedding_provider in {"local", "gemini"}:
            return False
        return bool(settings.openai_api_key)

    def _should_use_gemini(self) -> bool:
        if settings.embedding_provider == "gemini":
            return bool(settings.gemini_api_key)
        if settings.embedding_provider in {"local", "openai"}:
            return False
        if settings.openai_api_key:
            return False
        return bool(settings.gemini_api_key)

    def _openai_embed(self, text: str) -> list[float]:
        payload = {
            "input": text[:8000],
            "model": settings.embedding_model,
            "encoding_format": "float",
        }
        if settings.embedding_dimensions > 0 and settings.embedding_model.startswith("text-embedding-3"):
            payload["dimensions"] = settings.embedding_dimensions

        response = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["data"][0]["embedding"]

    def _gemini_embed(self, text: str) -> list[float]:
        model_name = settings.embedding_model
        if not model_name.startswith("gemini-embedding"):
            model_name = "gemini-embedding-001"

        config: dict[str, int] = {}
        if settings.embedding_dimensions > 0:
            config["outputDimensionality"] = settings.embedding_dimensions

        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:embedContent",
            headers={
                "x-goog-api-key": settings.gemini_api_key,
                "Content-Type": "application/json",
            },
            json={
                "model": f"models/{model_name}",
                "content": {
                    "parts": [
                        {
                            "text": text[:8000],
                        }
                    ]
                },
                **({"config": config} if config else {}),
            },
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()
        embeddings = payload.get("embedding") or {}
        return embeddings.get("values", [])

    @staticmethod
    def _local_embed(text: str, dimensions: int = 128) -> list[float]:
        vector_map: dict[int, float] = defaultdict(float)
        tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
        for token in tokens:
            if len(token) < 3:
                continue
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
            bucket = int(digest[:8], 16) % dimensions
            vector_map[bucket] += 1.0

        vector = [0.0] * dimensions
        for index, value in vector_map.items():
            vector[index] = value
        return vector


embedding_service = EmbeddingService()
