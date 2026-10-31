import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from pymongo.errors import PyMongoError

from app.repositories.memory_repository import MemoryRepository
from app.schemas.graph import GraphLink, GraphNode, GraphResponse
from app.schemas.memory import MemoryCreate, MemoryItem
from app.schemas.search import SearchAnswer, SearchCitation, SearchResponse, SearchResultItem
from app.schemas.summary import SummaryResponse
from app.schemas.timeline import TimelinePoint, TimelineResponse
from app.services.answer_service import AnswerContextItem, answer_service
from app.services.embedding_service import embedding_service
from app.services.enrichment_service import enrichment_service


@dataclass
class QueryContext:
    original_query: str
    normalized_query: str
    search_text: str
    tokens: list[str]
    expanded_terms: list[str]
    domain_hint: str | None
    inferred_time_range: str
    intent_label: str
    focused_memory_id: str | None = None
    resolved_query: str = ""


@dataclass
class MemoryChunk:
    memory: MemoryItem
    snippet: str
    score: float
    reason: str


class MemoryService:
    def __init__(self) -> None:
        self._repository = MemoryRepository()
        self._conversation_contexts: dict[str, dict[str, object]] = {}
        self._memories: list[MemoryItem] = [
            MemoryItem(
                id="mem_1",
                title="Building with Transformer Embeddings",
                url="https://example.com/transformers",
                summary="An article about embeddings, vector search, and retrieval systems.",
                content=(
                    "This article explains transformer embeddings, vector search, nearest-neighbor retrieval, "
                    "and how retrieval systems rank passages using semantic similarity."
                ),
                source_type="article",
                topics=["AI", "Transformers", "Search"],
                created_at=datetime(2026, 3, 10, 10, 0, tzinfo=UTC),
                last_visited_at=datetime(2026, 3, 10, 10, 0, tzinfo=UTC),
                visit_count=1,
            ),
            MemoryItem(
                id="mem_2",
                title="FastAPI for AI APIs",
                url="https://example.com/fastapi-ai",
                summary="A practical guide for building modern AI endpoints with FastAPI.",
                content=(
                    "The guide shows how to build FastAPI endpoints for AI applications, structure async APIs, "
                    "validate payloads, and serve embeddings and chat answers."
                ),
                source_type="documentation",
                topics=["FastAPI", "Backend", "Python"],
                created_at=datetime(2026, 4, 2, 15, 30, tzinfo=UTC),
                last_visited_at=datetime(2026, 4, 2, 15, 30, tzinfo=UTC),
                visit_count=1,
            ),
            MemoryItem(
                id="mem_3",
                title="LangChain Memory Workflows",
                url="https://example.com/langchain-memory",
                summary="Examples of semantic retrieval and memory pipelines for personal AI tools.",
                content=(
                    "Examples cover semantic retrieval, memory graphs, chunking documents, enriching saved pages, "
                    "and answering natural-language questions with retrieved context."
                ),
                source_type="repo",
                topics=["LangChain", "Memory", "AI"],
                created_at=datetime(2026, 4, 7, 9, 15, tzinfo=UTC),
                last_visited_at=datetime(2026, 4, 7, 9, 15, tzinfo=UTC),
                visit_count=1,
            ),
        ]

    def list_memories(self) -> list[MemoryItem]:
        try:
            if self._repository.available():
                return self._repository.list_memories()
        except PyMongoError:
            pass
        return sorted(self._memories, key=lambda item: item.created_at, reverse=True)

    def create_memory(self, payload: MemoryCreate) -> MemoryItem:
        try:
            if self._repository.available():
                return self._repository.create_memory(payload)
        except PyMongoError:
            pass

        now = datetime.now(UTC)
        memory = MemoryItem(
            id=str(uuid4()),
            title=payload.title,
            url=payload.url,
            summary=payload.summary,
            source_type=payload.source_type,
            topics=payload.topics,
            content=payload.content,
            created_at=now,
            last_visited_at=now,
            visit_count=1,
        )
        self._memories.insert(0, memory)
        return memory

    def enrich_memory(self, memory_id: str) -> MemoryItem | None:
        memories = self.list_memories()
        memory = next((item for item in memories if item.id == memory_id), None)
        if not memory:
            return None

        enriched_fields = enrichment_service.enrich_memory(memory)
        try:
            if self._repository.available():
                return self._repository.update_memory_fields(memory_id, enriched_fields)
        except PyMongoError:
            pass

        for index, item in enumerate(self._memories):
            if item.id == memory_id:
                updated = item.model_copy(update=enriched_fields)
                self._memories[index] = updated
                return updated
        return None

    def delete_memory(self, memory_id: str) -> bool:
        try:
            if self._repository.available():
                return self._repository.delete_memory(memory_id)
        except PyMongoError:
            pass

        before_count = len(self._memories)
        self._memories = [memory for memory in self._memories if memory.id != memory_id]
        return len(self._memories) < before_count

    def clear_memories(self) -> int:
        try:
            if self._repository.available():
                return self._repository.clear_memories()
        except PyMongoError:
            pass

        deleted_count = len(self._memories)
        self._memories = []
        return deleted_count

    def import_memories(self, payloads: list[MemoryCreate]) -> int:
        imported_count = 0
        for payload in payloads:
            memory = self.create_memory(payload)
            self.enrich_memory(memory.id)
            imported_count += 1
        return imported_count

    def search(
        self,
        query: str,
        mode: str = "keyword",
        time_range: str = "all",
        source_type: str = "all",
        sort_by: str = "relevance",
        conversation_id: str | None = None,
    ) -> SearchResponse:
        active_conversation_id = conversation_id or str(uuid4())
        context = self._build_query_context(query, time_range, active_conversation_id)
        all_items = self._apply_domain_hint(
            self._apply_source_filter(
                self._filter_by_time_range(self.list_memories(), context.inferred_time_range),
                source_type,
            ),
            context.domain_hint,
        )

        if context.focused_memory_id:
            all_items = [item for item in all_items if item.id == context.focused_memory_id] or all_items

        if not context.search_text:
            items = [
                SearchResultItem(memory=item, score=1.0, reason=self._time_reason(context.inferred_time_range))
                for item in all_items
            ]
        else:
            mode_key = mode.lower()
            if mode_key == "semantic":
                items = self._semantic_search(context, all_items)
            elif mode_key == "hybrid":
                items = self._hybrid_search(context, all_items)
            else:
                items = self._keyword_search(context, all_items)

        items = self._sort_results(items, sort_by)
        answer = self._build_answer(context, items)
        citations = self._build_citations(items, context)
        self._conversation_contexts[active_conversation_id] = {
            "query": context.resolved_query or context.original_query,
            "items": items[:5],
            "citations": citations[:5],
        }
        engine = embedding_service.provider_name() if mode.lower() in {"semantic", "hybrid"} else "keyword-ranker"
        return SearchResponse(
            query=query,
            resolved_query=context.resolved_query or context.original_query,
            mode=mode,
            engine=engine,
            applied_time_range=context.inferred_time_range,
            conversation_id=active_conversation_id,
            total=len(items),
            answer=answer,
            citations=citations,
            follow_up_suggestions=self._build_follow_up_suggestions(items),
            items=items,
        )

    def graph(self) -> GraphResponse:
        nodes = [GraphNode(id="user_1", label="You", type="user")]
        links: list[GraphLink] = []
        topic_ids: set[str] = set()
        source_ids: set[str] = set()
        seen_links: set[tuple[str, str, str]] = set()

        for memory in self.list_memories():
            memory_id = memory.id
            nodes.append(GraphNode(id=memory_id, label=memory.title, type="memory"))
            self._add_link(links, seen_links, "user_1", memory_id, "viewed")

            domain = self._extract_domain(memory.url)
            source_id = f"source_{domain}"
            if source_id not in source_ids:
                source_ids.add(source_id)
                nodes.append(GraphNode(id=source_id, label=domain, type="source"))
            self._add_link(links, seen_links, memory_id, source_id, "from")

            for topic in memory.topics:
                topic_key = topic.lower().replace(" ", "_")
                topic_id = f"topic_{topic_key}"
                if topic_id not in topic_ids:
                    topic_ids.add(topic_id)
                    nodes.append(GraphNode(id=topic_id, label=topic, type="topic"))
                self._add_link(links, seen_links, memory_id, topic_id, "mentions")

        return GraphResponse(nodes=nodes, links=links)

    def timeline(self) -> TimelineResponse:
        grouped_counts: dict[tuple[str, str], int] = defaultdict(int)
        for memory in self.list_memories():
            for topic in memory.topics[:2]:
                key = (memory.created_at.strftime("%Y-%m"), topic)
                grouped_counts[key] += 1

        points = [
            TimelinePoint(month=month, topic=topic, count=count)
            for (month, topic), count in sorted(grouped_counts.items())
        ]
        return TimelineResponse(points=points)

    def summary(self) -> SummaryResponse:
        memories = self.list_memories()
        topic_counts: dict[str, int] = defaultdict(int)
        source_counts: dict[str, int] = defaultdict(int)

        for memory in memories:
            for topic in memory.topics:
                topic_counts[topic] += 1
            source_counts[self._extract_domain(memory.url)] += 1

        top_topics = [
            topic for topic, _count in sorted(topic_counts.items(), key=lambda item: item[1], reverse=True)[:3]
        ]
        top_sources = [
            source for source, _count in sorted(source_counts.items(), key=lambda item: item[1], reverse=True)[:3]
        ]

        if memories:
            recent_titles = ", ".join(memory.title for memory in memories[:3])
            digest = (
                f"You have {len(memories)} saved memories. "
                f"Your strongest topics are {', '.join(top_topics) or 'still forming'}. "
                f"Recently captured items include {recent_titles}."
            )
        else:
            digest = "You have no saved memories yet. Start by capturing a page or adding one manually."

        return SummaryResponse(
            total_memories=len(memories),
            top_topics=top_topics,
            top_sources=top_sources,
            digest=digest,
        )

    def _keyword_search(self, context: QueryContext, items: list[MemoryItem]) -> list[SearchResultItem]:
        results: list[SearchResultItem] = []
        phrase = context.search_text
        for item in items:
            haystack = self._memory_text(item)
            score = 0.0
            reasons: list[str] = []

            if phrase and phrase in item.title.lower():
                score += 4.0
                reasons.append("Title phrase")
            if phrase and phrase in item.summary.lower():
                score += 3.0
                reasons.append("Summary phrase")
            if phrase and phrase in item.url.lower():
                score += 3.0
                reasons.append("URL phrase")

            token_hits = 0
            for term in context.expanded_terms:
                if term in item.title.lower():
                    score += 2.2
                    token_hits += 1
                elif term in item.summary.lower():
                    score += 1.6
                    token_hits += 1
                elif any(term in topic.lower() for topic in item.topics):
                    score += 1.8
                    token_hits += 1
                elif term in item.url.lower():
                    score += 1.4
                    token_hits += 1
                elif term in haystack:
                    score += 1.0
                    token_hits += 1

            if token_hits >= 2:
                reasons.append(f"{token_hits} query terms matched")

            if context.domain_hint and context.domain_hint in self._extract_domain(item.url).lower():
                score += 4.5
                reasons.append("Site match")

            if context.intent_label == "job openings" and self._has_job_signal(item):
                score += 3.4
                reasons.append("Job opening signal")

            if context.intent_label == "repositories" and ("github" in item.url.lower() or item.source_type.lower() == "repo"):
                score += 3.0
                reasons.append("Repository signal")

            if score > 0:
                results.append(
                    SearchResultItem(
                        memory=item,
                        score=round(score, 2),
                        reason=", ".join(reasons) or "Keyword match",
                    )
                )
        return sorted(results, key=lambda result: result.score, reverse=True)

    def _semantic_search(self, context: QueryContext, items: list[MemoryItem]) -> list[SearchResultItem]:
        results: list[SearchResultItem] = []
        semantic_query = " ".join(dict.fromkeys(context.expanded_terms)) or context.search_text
        for item in items:
            memory_text = self._memory_text(item)
            score = embedding_service.similarity(semantic_query, memory_text)
            if context.domain_hint and context.domain_hint in self._extract_domain(item.url).lower():
                score += 0.6
            if context.intent_label == "job openings" and self._has_job_signal(item):
                score += 0.5
            if score > 0:
                results.append(
                    SearchResultItem(
                        memory=item,
                        score=round(score, 3),
                        reason=f"Meaning-based similarity via {embedding_service.provider_name()}",
                    )
                )
        return sorted(results, key=lambda result: result.score, reverse=True)

    def _hybrid_search(self, context: QueryContext, items: list[MemoryItem]) -> list[SearchResultItem]:
        keyword_results = {result.memory.id: result for result in self._keyword_search(context, items)}
        semantic_results = {result.memory.id: result for result in self._semantic_search(context, items)}
        combined_ids = set(keyword_results) | set(semantic_results)
        combined: list[SearchResultItem] = []

        for memory_id in combined_ids:
            keyword_result = keyword_results.get(memory_id)
            semantic_result = semantic_results.get(memory_id)
            memory = (keyword_result or semantic_result).memory
            keyword_score = keyword_result.score if keyword_result else 0.0
            semantic_score = (semantic_result.score * 4) if semantic_result else 0.0
            reason_parts = []
            if keyword_result:
                reason_parts.append("Keyword")
            if semantic_result:
                reason_parts.append("Semantic")
            combined.append(
                SearchResultItem(
                    memory=memory,
                    score=round(keyword_score + semantic_score, 3),
                    reason=(" + ".join(reason_parts) or "Hybrid match") + f" via {embedding_service.provider_name()}",
                )
            )
        return sorted(combined, key=lambda result: result.score, reverse=True)

    def _build_answer(self, context: QueryContext, items: list[SearchResultItem]) -> SearchAnswer | None:
        if not items:
            return None

        top_chunks = self._select_context_chunks(context, items, limit=6)
        context_items = [
            AnswerContextItem(
                title=chunk.memory.title,
                url=chunk.memory.url,
                source_type=chunk.memory.source_type,
                snippet=chunk.snippet,
                relevance=chunk.reason,
            )
            for chunk in top_chunks
        ]

        answer = answer_service.answer_from_context(
            query=context.resolved_query or context.original_query or context.search_text,
            intent_label=context.intent_label,
            context_items=context_items,
        )
        if answer:
            return answer

        best = items[0]
        return SearchAnswer(
            headline=f"Best match for {context.intent_label}",
            summary=self._build_content_snippet(best.memory, context.search_text or context.normalized_query),
            exact_url=best.memory.url,
            match_reason=best.reason,
        )

    def _build_citations(self, items: list[SearchResultItem], context: QueryContext | None = None) -> list[SearchCitation]:
        top_chunks = self._select_context_chunks(context, items, limit=4) if context else []
        citations: list[SearchCitation] = []
        source_chunks = top_chunks or [
            MemoryChunk(
                memory=item.memory,
                snippet=self._build_content_snippet(item.memory, item.reason),
                score=item.score,
                reason=item.reason,
            )
            for item in items[:4]
        ]
        for chunk in source_chunks:
            citations.append(
                SearchCitation(
                    title=chunk.memory.title,
                    url=chunk.memory.url,
                    snippet=chunk.snippet,
                    source_type=chunk.memory.source_type,
                    relevance=self._compact_reason(chunk.reason),
                    memory_id=chunk.memory.id,
                )
            )
        return citations

    def _build_follow_up_suggestions(self, items: list[SearchResultItem]) -> list[str]:
        suggestions = [
            "show me the first one",
            "what did the second result say",
            "give me the exact URL again",
        ]
        if items:
            top = items[0].memory
            suggestions.append(f"what was interesting about {top.title[:28]}")
        return suggestions[:4]

    @staticmethod
    def _compact_reason(reason: str) -> str:
        compact = reason
        replacements = {
            "Title phrase": "Title",
            "Summary phrase": "Summary",
            "URL phrase": "URL",
            "direct passage match": "Passage",
            "Meaning-based similarity via": "Semantic via",
            "Keyword + Semantic via": "Hybrid via",
            "query terms matched": "term hits",
        }
        for source, target in replacements.items():
            compact = compact.replace(source, target)
        return compact[:110]

    def _build_query_context(self, query: str, time_range: str, conversation_id: str) -> QueryContext:
        normalized = query.strip().lower()
        conversation = self._conversation_contexts.get(conversation_id)
        focused_memory_id = self._resolve_follow_up_memory_id(normalized, conversation)
        if conversation and self._is_follow_up_query(normalized):
            title_terms = " ".join(
                citation.title for citation in conversation.get("citations", [])[:2] if getattr(citation, "title", "")
            )
            normalized = f"{normalized} {title_terms}".strip()

        inferred_time_range = self._infer_time_range(normalized, time_range)
        domain_hint = self._extract_domain_hint(normalized)
        tokens = self._tokenize_query(normalized)
        expanded_terms = self._expand_terms(tokens)
        search_text = " ".join(tokens)

        return QueryContext(
            original_query=query,
            normalized_query=normalized,
            search_text=search_text,
            tokens=tokens,
            expanded_terms=expanded_terms,
            domain_hint=domain_hint,
            inferred_time_range=inferred_time_range,
            intent_label=self._infer_intent(tokens),
            focused_memory_id=focused_memory_id,
            resolved_query=normalized,
        )

    @staticmethod
    def _tokenize_query(query: str) -> list[str]:
        stopwords = {
            "what", "which", "where", "show", "me", "the", "a", "an", "were", "was", "is", "are",
            "on", "in", "at", "for", "from", "to", "of", "that", "this", "did", "i", "my", "site",
            "page", "pages", "please", "about", "again"
        }
        raw_tokens = re.findall(r"[a-z0-9._-]+", query.lower())
        return [token for token in raw_tokens if token not in stopwords]

    @staticmethod
    def _expand_terms(tokens: list[str]) -> list[str]:
        expansions = {
            "job": ["jobs", "opening", "openings", "career", "careers", "hiring", "role", "roles", "vacancy"],
            "jobs": ["job", "opening", "openings", "career", "careers", "hiring", "role", "roles", "vacancy"],
            "opening": ["job", "jobs", "career", "careers", "hiring", "vacancy"],
            "openings": ["job", "jobs", "career", "careers", "hiring", "vacancy"],
            "career": ["job", "jobs", "opening", "openings", "hiring", "roles"],
            "repo": ["repository", "github", "project", "code"],
            "repos": ["repository", "github", "project", "code"],
            "documentation": ["docs", "guide", "reference"],
            "docs": ["documentation", "guide", "reference"],
        }
        merged: list[str] = []
        for token in tokens:
            merged.append(token)
            merged.extend(expansions.get(token, []))
        return list(dict.fromkeys(merged))

    @staticmethod
    def _infer_intent(tokens: list[str]) -> str:
        job_terms = {"job", "jobs", "opening", "openings", "career", "careers", "hiring", "vacancy", "role", "roles"}
        repo_terms = {"repo", "repos", "github", "repository", "project", "code"}
        doc_terms = {"docs", "documentation", "guide", "reference"}
        summary_terms = {"summarize", "summarise", "summary", "read", "learned", "learning"}
        if any(token in summary_terms for token in tokens):
            return "topic summary"
        if any(token in job_terms for token in tokens):
            return "job openings"
        if any(token in repo_terms for token in tokens):
            return "repositories"
        if any(token in doc_terms for token in tokens):
            return "documentation"
        return "memory recall"

    @staticmethod
    def _infer_time_range(query: str, selected_time_range: str) -> str:
        if selected_time_range.lower() != "all":
            return selected_time_range
        if "today" in query:
            return "today"
        if "this week" in query or "last week" in query or "week" in query:
            return "week"
        if "this month" in query or "last month" in query or "month" in query:
            return "month"
        return selected_time_range

    @staticmethod
    def _extract_domain_hint(query: str) -> str | None:
        before_site_match = re.search(r"([a-z0-9.-]+)\s+site\b", query)
        if before_site_match:
            return before_site_match.group(1).replace("www.", "")
        site_match = re.search(r"(?:site|domain)\s+([a-z0-9.-]+)", query)
        if site_match:
            return site_match.group(1).replace("www.", "")
        if ".com" in query or ".org" in query or ".in" in query or ".ai" in query:
            domain_match = re.search(r"([a-z0-9.-]+\.[a-z]{2,})", query)
            if domain_match:
                return domain_match.group(1).replace("www.", "")
        return None

    @staticmethod
    def _extract_domain(url: str) -> str:
        host = url.split("//")[-1].split("/")[0]
        return host or "unknown-source"

    @staticmethod
    def _is_follow_up_query(query: str) -> bool:
        return any(phrase in query for phrase in ["first one", "second", "third", "that one", "again", "exact url"])

    @staticmethod
    def _resolve_follow_up_memory_id(query: str, conversation: dict[str, object] | None) -> str | None:
        if not conversation:
            return None
        citations = conversation.get("citations", [])
        positions = {
            "first": 0,
            "second": 1,
            "third": 2,
        }
        for label, index in positions.items():
            if label in query and index < len(citations):
                citation = citations[index]
                return getattr(citation, "memory_id", None)
        if "that one" in query or "exact url" in query or "again" in query:
            if citations:
                return getattr(citations[0], "memory_id", None)
        return None

    @staticmethod
    def _memory_text(item: MemoryItem) -> str:
        return " ".join(
            [
                item.title,
                item.summary,
                item.content,
                " ".join(item.topics),
                item.url,
                MemoryService._extract_domain(item.url),
                item.source_type,
            ]
        ).lower()

    @staticmethod
    def _has_job_signal(item: MemoryItem) -> bool:
        text = MemoryService._memory_text(item)
        return any(term in text for term in ["job", "jobs", "career", "careers", "opening", "openings", "hiring", "role", "vacancy"])

    @staticmethod
    def _add_link(
        links: list[GraphLink],
        seen_links: set[tuple[str, str, str]],
        source: str,
        target: str,
        label: str,
    ) -> None:
        key = (source, target, label)
        if key not in seen_links:
            seen_links.add(key)
            links.append(GraphLink(source=source, target=target, label=label))

    @staticmethod
    def _filter_by_time_range(items: list[MemoryItem], time_range: str) -> list[MemoryItem]:
        now = datetime.now(UTC)
        range_key = time_range.lower()
        if range_key == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif range_key == "week":
            start = now - timedelta(days=7)
        elif range_key == "month":
            start = now - timedelta(days=30)
        else:
            return items

        return [item for item in items if (item.last_visited_at or item.created_at).replace(tzinfo=UTC) >= start]

    @staticmethod
    def _time_reason(time_range: str) -> str:
        labels = {"today": "Visited today", "week": "Visited this week", "month": "Visited this month"}
        return labels.get(time_range.lower(), "Recent memory")

    @staticmethod
    def _apply_source_filter(items: list[MemoryItem], source_type: str) -> list[MemoryItem]:
        if source_type.lower() == "all":
            return items
        return [item for item in items if item.source_type.lower() == source_type.lower()]

    @staticmethod
    def _apply_domain_hint(items: list[MemoryItem], domain_hint: str | None) -> list[MemoryItem]:
        if not domain_hint:
            return items
        domain_matches = [
            item for item in items
            if domain_hint in MemoryService._extract_domain(item.url).lower()
            or domain_hint in item.title.lower()
            or domain_hint in item.summary.lower()
        ]
        return domain_matches or items

    @staticmethod
    def _sort_results(results: list[SearchResultItem], sort_by: str) -> list[SearchResultItem]:
        key = sort_by.lower()
        if key == "recent":
            return sorted(results, key=lambda result: result.memory.last_visited_at or result.memory.created_at, reverse=True)
        if key == "visits":
            return sorted(results, key=lambda result: result.memory.visit_count, reverse=True)
        return sorted(results, key=lambda result: result.score, reverse=True)

    def _select_context_chunks(self, context: QueryContext | None, items: list[SearchResultItem], limit: int = 6) -> list[MemoryChunk]:
        if not items:
            return []
        query_text = ""
        expanded_terms: list[str] = []
        if context:
            query_text = context.search_text or context.normalized_query
            expanded_terms = context.expanded_terms

        chunks: list[MemoryChunk] = []
        for item in items[:5]:
            for snippet in self._chunk_memory_content(item.memory):
                score = self._score_chunk(snippet, query_text, expanded_terms) + item.score
                reason = item.reason
                if query_text and query_text.lower() in snippet.lower():
                    reason = f"{reason}, direct passage match"
                chunks.append(MemoryChunk(memory=item.memory, snippet=snippet, score=round(score, 3), reason=reason))

        ranked = sorted(chunks, key=lambda chunk: chunk.score, reverse=True)
        deduped: list[MemoryChunk] = []
        seen_pairs: set[tuple[str, str]] = set()
        for chunk in ranked:
            key = (chunk.memory.id, chunk.snippet[:90])
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            deduped.append(chunk)
            if len(deduped) >= limit:
                break
        return deduped

    @staticmethod
    def _chunk_memory_content(item: MemoryItem, chunk_size: int = 520, overlap: int = 120) -> list[str]:
        base_text = (item.content or item.summary or item.title).strip()
        if not base_text:
            return []
        if len(base_text) <= chunk_size:
            return [base_text]
        chunks: list[str] = []
        start = 0
        while start < len(base_text):
            end = min(len(base_text), start + chunk_size)
            chunk = base_text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(base_text):
                break
            start = max(end - overlap, start + 1)
        return chunks

    @staticmethod
    def _score_chunk(snippet: str, query_text: str, expanded_terms: list[str]) -> float:
        if not snippet:
            return 0.0
        lowered = snippet.lower()
        score = 0.0
        if query_text and query_text in lowered:
            score += 5.0
        overlap_hits = 0
        for term in expanded_terms:
            if term in lowered:
                score += 1.1
                overlap_hits += 1
        if overlap_hits:
            score += min(overlap_hits * 0.3, 2.0)
        if query_text:
            score += embedding_service.similarity(query_text, snippet) * 3
        return score

    @staticmethod
    def _build_content_snippet(item: MemoryItem, query: str) -> str:
        content = (item.content or item.summary or item.title).strip()
        if not content:
            return ""
        content = re.sub(r"\s+", " ", content).strip()
        lowered_content = content.lower()
        query_terms = [term for term in re.findall(r"[a-z0-9]+", query.lower()) if len(term) > 2]
        for term in query_terms:
            index = lowered_content.find(term)
            if index >= 0:
                start = max(0, index - 90)
                end = min(len(content), index + 170)
                snippet = content[start:end].strip(" ,.-")
                snippet = re.sub(r"\s+", " ", snippet)
                return snippet if start == 0 else f"... {snippet}"
        sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", content) if len(sentence.strip()) > 24]
        if sentences:
            return " ".join(sentences[:2])[:220].strip()
        return content[:220].strip()


memory_service = MemoryService()
