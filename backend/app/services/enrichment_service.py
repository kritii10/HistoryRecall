from __future__ import annotations

import re
from datetime import UTC, datetime

from app.schemas.memory import MemoryItem


class EnrichmentService:
    def enrich_memory(self, memory: MemoryItem) -> dict[str, object]:
        content = self._clean_text(memory.content or memory.summary or memory.title)
        summary = self._build_summary(memory, content)
        topics = self._infer_topics(memory, content)
        source_type = self._infer_source_type(memory, content)

        return {
            "content": content,
            "summary": summary,
            "topics": topics,
            "source_type": source_type,
            "enriched_at": datetime.now(UTC),
        }

    @staticmethod
    def _clean_text(text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip()
        boilerplate_patterns = [
            r"skip to main content",
            r"accept all cookies",
            r"privacy notice",
            r"cookie(s)? are strictly necessary",
            r"compile statistics of visits.*?services\.",
            r"use arrow keys to select.*?(?:miles|km)",
            r"search page search keyword.*?(?:distance search filters|job type)",
        ]
        for pattern in boilerplate_patterns:
            cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned[:12000]

    @staticmethod
    def _build_summary(memory: MemoryItem, content: str) -> str:
        if memory.summary and len(memory.summary.strip()) > 40:
            return memory.summary.strip()[:320]
        sentences = re.split(r"(?<=[.!?])\s+", content)
        useful_sentences = [
            sentence.strip()
            for sentence in sentences
            if sentence.strip() and len(sentence.strip()) > 30
        ]
        joined = " ".join(useful_sentences[:2])
        return (joined or memory.title).strip()[:320]

    @staticmethod
    def _infer_topics(memory: MemoryItem, content: str) -> list[str]:
        candidates = [
            "AI",
            "FastAPI",
            "Python",
            "React",
            "Search",
            "Graph",
            "LangChain",
            "MongoDB",
            "Neo4j",
            "Jobs",
            "Careers",
            "Cloud",
            "Data",
            "Backend",
            "Frontend",
            "OpenAI",
            "Gemini",
        ]
        lowered = f"{memory.title} {memory.summary} {content}".lower()
        found = [topic for topic in candidates if topic.lower() in lowered]
        merged = list(dict.fromkeys(memory.topics + found))
        return merged[:8]

    @staticmethod
    def _infer_source_type(memory: MemoryItem, content: str) -> str:
        lowered = f"{memory.title} {memory.url} {content}".lower()
        if "github.com" in lowered:
            return "repo"
        if any(term in lowered for term in ["docs", "documentation", "reference", "api guide"]):
            return "documentation"
        if any(term in lowered for term in ["career", "careers", "job", "jobs", "hiring", "vacancy"]):
            return "webpage"
        if any(term in lowered for term in ["article", "blog", "read time"]):
            return "article"
        return memory.source_type or "webpage"


enrichment_service = EnrichmentService()
