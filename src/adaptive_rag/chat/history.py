"""Rolling history preparation for long multi-turn chat sessions.

Keeps the most recent turns verbatim and compresses older ones into a
deterministic summary so the runner prompt stays bounded without an extra
LLM call (Token Plan safe).

User-stated preferences and declarative facts are pinned into the summary so
they survive truncation even when older exchanges are omitted (closes the
memory-vs-retrieval gap for facts not present in the knowledge base).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from adaptive_rag.chat.models import ChatHistoryTurn

# How many most-recent user/assistant messages stay verbatim.
DEFAULT_KEEP_RECENT = 8
# Max messages loaded from audit before summarization (pair-ish).
DEFAULT_HISTORY_LOAD_LIMIT = 64
# Cap summary size injected into the prompt.
DEFAULT_MAX_SUMMARY_CHARS = 2_400
# Always keep this many pinned user-stated fact lines at the top of the summary.
DEFAULT_PINNED_FACT_SLOTS = 12


@dataclass(frozen=True, slots=True)
class PreparedChatHistory:
    """History ready for the runner, plus inspector-facing metadata."""

    turns: tuple[ChatHistoryTurn, ...]
    summary: str | None
    total_messages: int
    kept_recent: int
    summarized_messages: int
    pinned_facts: tuple[str, ...] = ()

    @property
    def used_summary(self) -> bool:
        return self.summarized_messages > 0 and bool(self.summary)

    def as_step_detail(self) -> dict[str, object]:
        detail: dict[str, object] = {
            "total_messages": self.total_messages,
            "kept_recent": self.kept_recent,
            "summarized_messages": self.summarized_messages,
            "used_summary": self.used_summary,
            "pinned_facts": len(self.pinned_facts),
        }
        if self.summary:
            preview = (
                self.summary if len(self.summary) <= 240 else self.summary[:237] + "..."
            )
            detail["summary_preview"] = preview
        if self.pinned_facts:
            detail["pinned_fact_preview"] = list(self.pinned_facts[:4])
        return detail


def prepare_chat_history(
    raw_turns: Sequence[tuple[str, str]] | Sequence[ChatHistoryTurn],
    *,
    keep_recent: int = DEFAULT_KEEP_RECENT,
    max_summary_chars: int = DEFAULT_MAX_SUMMARY_CHARS,
    pinned_fact_slots: int = DEFAULT_PINNED_FACT_SLOTS,
) -> PreparedChatHistory:
    """Compress older turns when the transcript exceeds ``keep_recent``.

    ``raw_turns`` may be ``(role, content)`` pairs or ``ChatHistoryTurn``s,
    oldest-first.
    """

    turns = _normalize_turns(raw_turns)
    total = len(turns)
    if keep_recent < 1:
        keep_recent = DEFAULT_KEEP_RECENT
    if total <= keep_recent:
        return PreparedChatHistory(
            turns=turns,
            summary=None,
            total_messages=total,
            kept_recent=total,
            summarized_messages=0,
            pinned_facts=(),
        )

    older = turns[:-keep_recent]
    recent = turns[-keep_recent:]
    pinned = _extract_pinned_facts(older, limit=pinned_fact_slots)
    summary = _summarize_turns(
        older,
        max_chars=max_summary_chars,
        pinned_facts=pinned,
    )
    bridge = (
        ChatHistoryTurn(
            role="user",
            content=(
                "[Earlier conversation — condensed for context]\n"
                f"{summary}\n"
                "[End of condensed context]\n"
                "Treat user-stated preferences and facts in the condensed "
                "context as authoritative for this thread even when retrieval "
                "returns no matching sources."
            ),
        ),
        ChatHistoryTurn(
            role="assistant",
            content=(
                "Understood. I will use the condensed earlier context and any "
                "pinned user-stated facts when answering follow-ups, including "
                "facts that are not in the knowledge base."
            ),
        ),
    )
    return PreparedChatHistory(
        turns=bridge + recent,
        summary=summary,
        total_messages=total,
        kept_recent=len(recent),
        summarized_messages=len(older),
        pinned_facts=pinned,
    )


def _normalize_turns(
    raw_turns: Sequence[tuple[str, str]] | Sequence[ChatHistoryTurn],
) -> tuple[ChatHistoryTurn, ...]:
    normalized: list[ChatHistoryTurn] = []
    for item in raw_turns:
        if isinstance(item, ChatHistoryTurn):
            role = item.role
            content = item.content
        else:
            role, content = item
        role = str(role).strip()
        content = str(content).strip()
        if role not in {"user", "assistant"} or not content:
            continue
        normalized.append(ChatHistoryTurn(role=role, content=content))
    return tuple(normalized)


# Patterns that mark a user turn as a durable preference / declarative fact.
# Keep these specific so ordinary questions ("What is X?") are not pinned.
_PIN_USER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(i prefer|i like|i want|i need|please always|always use)\b", re.I),
    re.compile(r"\b(my name is|call me)\b", re.I),
    re.compile(r"\b(remember that|note that|for the record|from now on)\b", re.I),
    re.compile(r"\b(my favorite|favourite)\b", re.I),
    re.compile(r"\b(do not|don't|never)\b.+\b(again|ever|please)\b", re.I),
    re.compile(r"\bmy\s+\w[\w\s]{0,40}\bis\b", re.I),
)


def _is_pinnable_user_fact(text: str) -> bool:
    collapsed = " ".join(text.split())
    if len(collapsed) < 8 or len(collapsed) > 280:
        return False
    return any(pattern.search(collapsed) for pattern in _PIN_USER_PATTERNS)


def _extract_pinned_facts(
    turns: Sequence[ChatHistoryTurn],
    *,
    limit: int,
) -> tuple[str, ...]:
    """Collect durable user-stated facts from older turns (oldest first)."""

    facts: list[str] = []
    seen: set[str] = set()
    for turn in turns:
        if turn.role != "user":
            continue
        if not _is_pinnable_user_fact(turn.content):
            continue
        line = _clip(turn.content, 200)
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        facts.append(line)
    # Prefer the most recent pinned facts if over limit.
    if len(facts) > limit:
        facts = facts[-limit:]
    return tuple(facts)


def _summarize_turns(
    turns: Sequence[ChatHistoryTurn],
    *,
    max_chars: int,
    pinned_facts: Sequence[str] = (),
) -> str:
    """Build a compact bullet list of older Q/A without an LLM."""

    sections: list[str] = []
    if pinned_facts:
        sections.append("Pinned user-stated facts (authoritative for this thread):")
        for fact in pinned_facts:
            sections.append(f"- USER_FACT: {fact}")
        sections.append("")

    bullets: list[str] = []
    pending_user: str | None = None
    for turn in turns:
        if turn.role == "user":
            pending_user = _clip(turn.content, 160)
        elif turn.role == "assistant":
            answer = _clip(turn.content, 120)
            if pending_user is not None:
                bullets.append(f"- User: {pending_user} → Assistant: {answer}")
                pending_user = None
            else:
                bullets.append(f"- Assistant: {answer}")
    if pending_user is not None:
        bullets.append(f"- User: {pending_user}")

    if not bullets and not pinned_facts:
        return "No earlier substantive turns."

    pinned_block = "\n".join(sections).rstrip()
    # Reserve space for pinned facts first.
    remaining = max_chars - (len(pinned_block) + 2 if pinned_block else 0)
    if remaining < 200:
        remaining = max(200, max_chars // 3)

    if not bullets:
        text = pinned_block
    else:
        body = "\n".join(bullets)
        if len(body) > remaining:
            kept: list[str] = []
            size = 0
            for bullet in reversed(bullets):
                add = len(bullet) + (1 if kept else 0)
                if size + add > remaining - 40:
                    break
                kept.append(bullet)
                size += add
            kept.reverse()
            omitted = len(bullets) - len(kept)
            if omitted > 0:
                kept.insert(0, f"- …({omitted} earlier exchanges omitted)")
            body = "\n".join(kept)
        if pinned_block:
            text = f"{pinned_block}\n\nExchange log:\n{body}"
        else:
            text = body

    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _clip(text: str, max_len: int) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= max_len:
        return collapsed
    return collapsed[: max_len - 1].rstrip() + "…"
