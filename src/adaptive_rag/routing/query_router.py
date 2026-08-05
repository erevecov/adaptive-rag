"""Lightweight rule-based query router (no hosted LLM by default)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Protocol

QueryRoute = Literal["skip_retrieval", "dense_sparse", "graph"]

_SKIP_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"^\s*(hi|hello|hey|hola|thanks|thank you|gracias|ok|okay|bye|goodbye)"
        r"\s*[!.?]*\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(how are you|what can you do|who are you)\s*[?.!]?\s*$",
        re.IGNORECASE,
    ),
)

_GRAPH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(how (are|is|was).+\brelated\b|related to|connected to|"
        r"relationship between|who works with|depends on)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(graph|entity|entities|knowledge graph)\b", re.IGNORECASE),
)


@dataclass(frozen=True, slots=True)
class QueryRouteDecision:
    route: QueryRoute
    reason: str
    strategy: str


class QueryRouter(Protocol):
    def route(self, query: str, *, graph_ready: bool = False) -> QueryRouteDecision: ...


class RuleBasedQueryRouter:
    def route(self, query: str, *, graph_ready: bool = False) -> QueryRouteDecision:
        normalized = " ".join(query.strip().split())
        if not normalized:
            return QueryRouteDecision(
                route="dense_sparse",
                reason="empty_query_fallback",
                strategy="dense_sparse",
            )
        for pattern in _SKIP_PATTERNS:
            if pattern.search(normalized):
                return QueryRouteDecision(
                    route="skip_retrieval",
                    reason="greeting_or_meta_skip",
                    strategy="skip_retrieval",
                )
        for pattern in _GRAPH_PATTERNS:
            if pattern.search(normalized):
                if graph_ready:
                    return QueryRouteDecision(
                        route="graph",
                        reason="graph_pattern_graph_ready",
                        strategy="graph",
                    )
                return QueryRouteDecision(
                    route="dense_sparse",
                    reason="graph_pattern_graph_not_ready",
                    strategy="dense_sparse",
                )
        return QueryRouteDecision(
            route="dense_sparse",
            reason="default_dense_sparse",
            strategy="dense_sparse",
        )
