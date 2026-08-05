"""Conversational query condensation for multi-turn retrieval."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from adaptive_rag.chat.models import ChatHistoryTurn


class QueryCondenser(Protocol):
    def condense(
        self,
        *,
        history: Sequence[ChatHistoryTurn],
        message: str,
    ) -> str:
        """Return a self-contained retrieval query for the latest user message."""


class DeterministicQueryCondenser:
    """Offline/test condenser: stitch last user context with the follow-up."""

    def condense(
        self,
        *,
        history: Sequence[ChatHistoryTurn],
        message: str,
    ) -> str:
        trimmed = message.strip()
        if not history:
            return trimmed

        prior_users = [
            turn.content.strip()
            for turn in history
            if turn.role == "user" and turn.content.strip()
        ]
        if not prior_users:
            return trimmed

        # Follow-ups that look self-contained stay as-is.
        if _looks_self_contained(trimmed):
            return trimmed

        last_user = prior_users[-1]
        if trimmed.lower() in last_user.lower():
            return trimmed
        return f"{last_user} — {trimmed}"


def _looks_self_contained(message: str) -> bool:
    lowered = message.lower()
    pronouns = ("it", "that", "this", "they", "them", "those", "these")
    tokens = {token.strip(".,?!") for token in lowered.split()}
    if tokens & set(pronouns):
        return False
    if lowered.startswith(("what about", "and ", "also ", "how about")):
        return False
    return len(message.split()) >= 6
