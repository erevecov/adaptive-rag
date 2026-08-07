"""Rolling history preparation for long multi-turn chat sessions.

Keeps the most recent turns verbatim and compresses older ones into a
deterministic summary so the runner prompt stays bounded without an extra
LLM call (Token Plan safe).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from adaptive_rag.chat.models import ChatHistoryTurn

# How many most-recent user/assistant messages stay verbatim.
DEFAULT_KEEP_RECENT = 6
# Max messages loaded from audit before summarization (pair-ish).
DEFAULT_HISTORY_LOAD_LIMIT = 48
# Cap summary size injected into the prompt.
DEFAULT_MAX_SUMMARY_CHARS = 1_800


@dataclass(frozen=True, slots=True)
class PreparedChatHistory:
    """History ready for the runner, plus inspector-facing metadata."""

    turns: tuple[ChatHistoryTurn, ...]
    summary: str | None
    total_messages: int
    kept_recent: int
    summarized_messages: int

    @property
    def used_summary(self) -> bool:
        return self.summarized_messages > 0 and bool(self.summary)

    def as_step_detail(self) -> dict[str, object]:
        detail: dict[str, object] = {
            "total_messages": self.total_messages,
            "kept_recent": self.kept_recent,
            "summarized_messages": self.summarized_messages,
            "used_summary": self.used_summary,
        }
        if self.summary:
            preview = self.summary if len(self.summary) <= 240 else self.summary[:237] + "..."
            detail["summary_preview"] = preview
        return detail


def prepare_chat_history(
    raw_turns: Sequence[tuple[str, str]] | Sequence[ChatHistoryTurn],
    *,
    keep_recent: int = DEFAULT_KEEP_RECENT,
    max_summary_chars: int = DEFAULT_MAX_SUMMARY_CHARS,
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
        )

    older = turns[:-keep_recent]
    recent = turns[-keep_recent:]
    summary = _summarize_turns(older, max_chars=max_summary_chars)
    bridge = (
        ChatHistoryTurn(
            role="user",
            content=(
                "[Earlier conversation — condensed for context]\n"
                f"{summary}\n"
                "[End of condensed context]"
            ),
        ),
        ChatHistoryTurn(
            role="assistant",
            content=(
                "Understood. I will use the condensed earlier context when "
                "answering follow-ups."
            ),
        ),
    )
    return PreparedChatHistory(
        turns=bridge + recent,
        summary=summary,
        total_messages=total,
        kept_recent=len(recent),
        summarized_messages=len(older),
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


def _summarize_turns(
    turns: Sequence[ChatHistoryTurn],
    *,
    max_chars: int,
) -> str:
    """Build a compact bullet list of older Q/A without an LLM."""

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

    if not bullets:
        return "No earlier substantive turns."

    text = "\n".join(bullets)
    if len(text) <= max_chars:
        return text
    # Prefer keeping the most recent older bullets when truncating.
    kept: list[str] = []
    size = 0
    for bullet in reversed(bullets):
        add = len(bullet) + (1 if kept else 0)
        if size + add > max_chars - 20:
            break
        kept.append(bullet)
        size += add
    kept.reverse()
    omitted = len(bullets) - len(kept)
    if omitted > 0:
        kept.insert(0, f"- …({omitted} earlier exchanges omitted)")
    return "\n".join(kept)


def _clip(text: str, max_len: int) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= max_len:
        return collapsed
    return collapsed[: max_len - 1].rstrip() + "…"
