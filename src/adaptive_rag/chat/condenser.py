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
    """Offline/test condenser: stitch last context with the follow-up.

    Beflow parity (local-first): resolve pronouns / ellipsis / short
    confirmations against recent turns without an LLM call. Self-contained
    messages stay verbatim. Spanish + English openers are covered.
    """

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
        prior_assistants = [
            turn.content.strip()
            for turn in history
            if turn.role == "assistant" and turn.content.strip()
        ]
        if not prior_users and not prior_assistants:
            return trimmed

        # Short confirmations resolve against the last assistant proposal.
        if _is_short_confirmation(trimmed) and prior_assistants:
            last_assistant = prior_assistants[-1]
            return f"{last_assistant} — {trimmed}"

        # Follow-ups that look self-contained stay as-is.
        if _looks_self_contained(trimmed):
            return trimmed

        anchor = prior_users[-1] if prior_users else prior_assistants[-1]
        if trimmed.lower() in anchor.lower():
            return trimmed
        return f"{anchor} — {trimmed}"


_SHORT_CONFIRMATIONS = frozenset(
    {
        "ok",
        "okay",
        "yes",
        "yep",
        "yeah",
        "sure",
        "please",
        "go",
        "do it",
        "proceed",
        "dale",
        "si",
        "sí",
        "okey",
        "hazlo",
        "procede",
        "claro",
        "va",
        "listo",
    }
)

_FOLLOW_UP_OPENERS = (
    "what about",
    "how about",
    "and ",
    "also ",
    "y ",
    "tambien ",
    "también ",
    "que tal ",
    "qué tal ",
    "cuanto ",
    "cuánto ",
    "como ",
    "cómo ",
)


def _is_short_confirmation(message: str) -> bool:
    lowered = message.lower().strip().strip(".!?,")
    if lowered in _SHORT_CONFIRMATIONS:
        return True
    return len(lowered.split()) <= 2 and lowered in _SHORT_CONFIRMATIONS


def _looks_self_contained(message: str) -> bool:
    lowered = message.lower()
    pronouns = (
        "it",
        "that",
        "this",
        "they",
        "them",
        "those",
        "these",
        "eso",
        "esa",
        "ese",
        "esto",
        "esta",
        "este",
        "ellos",
        "ellas",
        "lo",
        "la",
        "los",
        "las",
    )
    tokens = {token.strip(".,?!") for token in lowered.split()}
    if tokens & set(pronouns):
        return False
    if any(lowered.startswith(opener) for opener in _FOLLOW_UP_OPENERS):
        return False
    # Single-token / very short fragments are almost never retrieval-ready.
    if len(message.split()) < 4:
        return False
    return len(message.split()) >= 6
