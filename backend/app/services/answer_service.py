from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.schemas.search import SearchAnswer


@dataclass
class AnswerContextItem:
    title: str
    url: str
    source_type: str
    snippet: str
    relevance: str


class AnswerService:
    def answer_from_context(
        self,
        query: str,
        intent_label: str,
        context_items: list[AnswerContextItem],
    ) -> SearchAnswer | None:
        if not context_items:
            return None

        if settings.answer_provider == "openai" and settings.openai_api_key:
            try:
                return self._openai_answer(query, intent_label, context_items)
            except Exception:
                pass

        if settings.answer_provider == "gemini" and settings.gemini_api_key:
            try:
                return self._gemini_answer(query, intent_label, context_items)
            except Exception:
                pass

        if settings.openai_api_key:
            try:
                return self._openai_answer(query, intent_label, context_items)
            except Exception:
                pass

        if settings.gemini_api_key:
            try:
                return self._gemini_answer(query, intent_label, context_items)
            except Exception:
                pass

        top = context_items[0]
        supporting = [item.title for item in context_items[:3]]
        summary, key_points = self._fallback_summary(query, intent_label, context_items)
        return SearchAnswer(
            headline=self._fallback_headline(intent_label, context_items),
            summary=summary,
            exact_url=top.url,
            match_reason=f"{top.relevance}. Synthesized from {', '.join(supporting)}",
            key_points=key_points,
        )

    def _openai_answer(
        self,
        query: str,
        intent_label: str,
        context_items: list[AnswerContextItem],
    ) -> SearchAnswer:
        prompt = self._build_prompt(query, intent_label, context_items)
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.answer_model,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Answer only from the provided browsing archive context. "
                            "Synthesize across multiple passages when useful, but do not invent facts. "
                            "Return JSON with keys headline, summary, exact_url, match_reason, key_points. "
                            "exact_url should be the single most actionable source page. "
                            "key_points should be a short list of specific takeaways from the archived pages. "
                            "If context is weak, pick the best available page and say that clearly."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        data = json.loads(content)
        return SearchAnswer(
            headline=data.get("headline", f"Best match for {intent_label}"),
            summary=data.get("summary", context_items[0].snippet),
            exact_url=data.get("exact_url", context_items[0].url),
            match_reason=data.get("match_reason", context_items[0].relevance),
            key_points=data.get("key_points", []),
        )

    def _gemini_answer(
        self,
        query: str,
        intent_label: str,
        context_items: list[AnswerContextItem],
    ) -> SearchAnswer:
        prompt = self._build_prompt(query, intent_label, context_items)
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.answer_model}:generateContent",
            headers={
                "x-goog-api-key": settings.gemini_api_key,
                "Content-Type": "application/json",
            },
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": (
                                    "Answer only from the provided browsing archive context. "
                                    "Synthesize across multiple passages when useful, but do not invent facts. "
                                    "Return JSON with keys headline, summary, exact_url, match_reason, key_points. "
                                    "exact_url should be the single most actionable source page.\n\n"
                                    + prompt
                                )
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json",
                },
            },
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(content)
        return SearchAnswer(
            headline=data.get("headline", f"Best match for {intent_label}"),
            summary=data.get("summary", context_items[0].snippet),
            exact_url=data.get("exact_url", context_items[0].url),
            match_reason=data.get("match_reason", context_items[0].relevance),
            key_points=data.get("key_points", []),
        )

    @staticmethod
    def _build_prompt(query: str, intent_label: str, context_items: list[AnswerContextItem]) -> str:
        lines = [f"User question: {query}", f"Intent: {intent_label}", "Context pages:"]
        for index, item in enumerate(context_items, start=1):
            lines.extend(
                [
                    f"{index}. title: {item.title}",
                    f"   url: {item.url}",
                    f"   source_type: {item.source_type}",
                    f"   reason: {item.relevance}",
                    f"   snippet: {item.snippet}",
                ]
            )
        return "\n".join(lines)

    @staticmethod
    def _fallback_summary(
        query: str,
        intent_label: str,
        context_items: list[AnswerContextItem],
    ) -> tuple[str, list[str]]:
        top = context_items[0]
        if len(context_items) == 1:
            return top.snippet, [f"Most relevant source: {top.title}"]
        second = context_items[1]
        if intent_label == "topic summary":
            return (
                f"Across the saved pages, the main theme around '{query}' is reflected in {top.title} and {second.title}. "
                f"The archive suggests: {top.snippet}",
                [
                    f"{top.title}: {top.snippet[:120]}",
                    f"{second.title}: {second.snippet[:120]}",
                    f"Primary source to reopen: {top.url}",
                ],
            )
        return (
            f"For '{query}', the strongest archived match is {top.title}. "
            f"Key evidence: {top.snippet} "
            f"Related context from {second.title}: {second.snippet}",
            [
                f"Best source: {top.title}",
                f"Related source: {second.title}",
                f"Open this page for detail: {top.url}",
            ],
        )

    @staticmethod
    def _fallback_headline(intent_label: str, context_items: list[AnswerContextItem]) -> str:
        if intent_label == "topic summary":
            return "Summary of what you read"
        return f"Best match for {intent_label}"


answer_service = AnswerService()
