"""Chunking semantico Markdown baseline."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import tiktoken
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Chunk, DocumentVersion
from adaptive_rag.db.repositories import ChunkRepository, DocumentRepository

CHUNKER_VERSION = "semantic_markdown_v1"
_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_LIST_PATTERN = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
_TABLE_SEPARATOR_PATTERN = re.compile(
    r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$"
)
_WORD_WITH_TRAILING_SPACE_PATTERN = re.compile(r"\S+\s*")


class TokenEstimator(Protocol):
    name: str

    def count(self, text: str) -> int:
        """Devuelve un conteo deterministico de tokens estimados."""


class ChunkingPipelineError(ValueError):
    """Error no retryable del baseline de chunking."""


@dataclass(frozen=True, slots=True)
class SemanticMarkdownChunkerConfig:
    target_chunk_tokens: int = 500
    max_chunk_tokens: int = 800
    overlap_tokens: int = 80
    encoding_name: str = "o200k_base"

    def __post_init__(self) -> None:
        if self.target_chunk_tokens <= 0:
            raise ValueError("target_chunk_tokens must be positive")
        if self.max_chunk_tokens < self.target_chunk_tokens:
            raise ValueError("max_chunk_tokens must be >= target_chunk_tokens")
        if self.overlap_tokens < 0:
            raise ValueError("overlap_tokens must be non-negative")
        if self.overlap_tokens >= self.target_chunk_tokens:
            raise ValueError("overlap_tokens must be < target_chunk_tokens")

    def as_metadata(self) -> dict[str, Any]:
        return {
            "encoding_name": self.encoding_name,
            "max_chunk_tokens": self.max_chunk_tokens,
            "overlap_tokens": self.overlap_tokens,
            "target_chunk_tokens": self.target_chunk_tokens,
        }


@dataclass(frozen=True, slots=True)
class ChunkPlan:
    ordinal: int
    char_start: int
    char_end: int
    token_count: int
    section_metadata: Mapping[str, Any]
    chunker_metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ChunkingRunResult:
    document_version: DocumentVersion
    chunks: list[Chunk]
    created_chunks: bool


@dataclass(frozen=True, slots=True)
class _MarkdownBlock:
    start: int
    end: int
    kind: str
    section_path: tuple[str, ...]
    heading: str | None


@dataclass(frozen=True, slots=True)
class _Line:
    start: int
    end: int
    text: str


class TiktokenTokenEstimator:
    """Token estimator local basado en tiktoken."""

    def __init__(self, encoding_name: str = "o200k_base") -> None:
        self.name = f"tiktoken:{encoding_name}"
        self._encoding = tiktoken.get_encoding(encoding_name)

    def count(self, text: str) -> int:
        return len(self._encoding.encode(text, disallowed_special=()))


class SemanticMarkdownChunker:
    """Chunker `semantic_markdown_v1` structure-first con fallback por tokens."""

    def __init__(
        self,
        *,
        token_estimator: TokenEstimator | None = None,
        config: SemanticMarkdownChunkerConfig | None = None,
    ) -> None:
        self.config = config or SemanticMarkdownChunkerConfig()
        self.token_estimator = token_estimator or TiktokenTokenEstimator(
            self.config.encoding_name
        )
        self.chunker_config_hash = _hash_config(
            config=self.config,
            token_estimator_name=self.token_estimator.name,
        )

    def chunk(self, text: str) -> list[ChunkPlan]:
        if not text:
            raise ChunkingPipelineError("document version text is empty")

        blocks = self._split_oversized_blocks(self._parse_blocks(text), text)
        chunks: list[ChunkPlan] = []
        current: list[_MarkdownBlock] = []

        for block in blocks:
            if block.kind == "heading" and current:
                chunks.append(
                    self._plan_chunk(text=text, blocks=current, chunks=chunks)
                )
                current = []

            candidate = [*current, block]
            candidate_tokens = self._count_span(
                text, candidate[0].start, candidate[-1].end
            )
            if current and candidate_tokens > self.config.target_chunk_tokens:
                chunks.append(
                    self._plan_chunk(text=text, blocks=current, chunks=chunks)
                )
                current = [block]
                continue

            current = candidate

        if current:
            chunks.append(self._plan_chunk(text=text, blocks=current, chunks=chunks))

        return chunks

    def _parse_blocks(self, text: str) -> list[_MarkdownBlock]:
        lines = _split_lines(text)
        blocks: list[_MarkdownBlock] = []
        section_stack: list[str] = []
        current_heading: str | None = None
        index = 0

        while index < len(lines):
            if _is_blank(lines[index].text):
                start_index = index
                index = _consume_blank_lines(lines, index)
                blocks.append(
                    _MarkdownBlock(
                        start=lines[start_index].start,
                        end=lines[index - 1].end,
                        kind="blank",
                        section_path=tuple(section_stack),
                        heading=current_heading,
                    )
                )
                continue

            heading_match = _HEADING_PATTERN.match(lines[index].text.strip())
            if heading_match is not None:
                level = len(heading_match.group(1))
                heading = heading_match.group(2).strip()
                section_stack = [*section_stack[: level - 1], heading]
                current_heading = heading
                start_index = index
                index += 1
                index = _consume_blank_lines(lines, index)
                blocks.append(
                    _MarkdownBlock(
                        start=lines[start_index].start,
                        end=lines[index - 1].end,
                        kind="heading",
                        section_path=tuple(section_stack),
                        heading=current_heading,
                    )
                )
                continue

            start_index = index
            if _starts_code_fence(lines[index].text):
                index = _consume_code_fence(lines, index)
            elif _starts_table(lines, index):
                index = _consume_table(lines, index)
            elif _LIST_PATTERN.match(lines[index].text) is not None:
                index = _consume_list(lines, index)
            else:
                index = _consume_paragraph(lines, index)

            index = _consume_blank_lines(lines, index)
            blocks.append(
                _MarkdownBlock(
                    start=lines[start_index].start,
                    end=lines[index - 1].end,
                    kind="content",
                    section_path=tuple(section_stack),
                    heading=current_heading,
                )
            )

        return blocks

    def _split_oversized_blocks(
        self, blocks: list[_MarkdownBlock], text: str
    ) -> list[_MarkdownBlock]:
        split_blocks: list[_MarkdownBlock] = []
        for block in blocks:
            if (
                self._count_span(text, block.start, block.end)
                <= self.config.max_chunk_tokens
            ):
                split_blocks.append(block)
                continue
            split_blocks.extend(self._split_block_by_tokens(block=block, text=text))
        return split_blocks

    def _split_block_by_tokens(
        self, *, block: _MarkdownBlock, text: str
    ) -> list[_MarkdownBlock]:
        block_text = text[block.start : block.end]
        parts = list(_WORD_WITH_TRAILING_SPACE_PATTERN.finditer(block_text))
        if not parts:
            return [block]

        split_blocks: list[_MarkdownBlock] = []
        current_start = block.start
        current_end = block.start
        for part in parts:
            candidate_end = block.start + part.end()
            candidate_tokens = self._count_span(text, current_start, candidate_end)
            if (
                current_end > current_start
                and candidate_tokens > self.config.target_chunk_tokens
            ):
                split_blocks.append(
                    _MarkdownBlock(
                        start=current_start,
                        end=current_end,
                        kind=block.kind,
                        section_path=block.section_path,
                        heading=block.heading,
                    )
                )
                current_start = current_end
            current_end = candidate_end

        if current_end > current_start:
            split_blocks.append(
                _MarkdownBlock(
                    start=current_start,
                    end=current_end,
                    kind=block.kind,
                    section_path=block.section_path,
                    heading=block.heading,
                )
            )
        return split_blocks

    def _plan_chunk(
        self,
        *,
        text: str,
        blocks: list[_MarkdownBlock],
        chunks: list[ChunkPlan],
    ) -> ChunkPlan:
        base_start = blocks[0].start
        end = blocks[-1].end
        start = self._overlap_start(
            text=text,
            base_start=base_start,
            end=end,
            chunks=chunks,
        )
        section_block = _first_non_blank(blocks)
        return ChunkPlan(
            ordinal=len(chunks),
            char_start=start,
            char_end=end,
            token_count=self._count_span(text, start, end),
            section_metadata={
                "heading": section_block.heading,
                "section_path": list(section_block.section_path),
            },
            chunker_metadata={
                "chunker_config_hash": self.chunker_config_hash,
                "chunker_version": CHUNKER_VERSION,
                "config": self.config.as_metadata(),
                "token_estimator": self.token_estimator.name,
            },
        )

    def _count_span(self, text: str, start: int, end: int) -> int:
        return self.token_estimator.count(text[start:end])

    def _overlap_start(
        self,
        *,
        text: str,
        base_start: int,
        end: int,
        chunks: list[ChunkPlan],
    ) -> int:
        if not chunks or self.config.overlap_tokens == 0:
            return base_start

        previous_chunk = chunks[-1]
        candidate = base_start
        previous_text = text[previous_chunk.char_start : base_start]
        matches = list(_WORD_WITH_TRAILING_SPACE_PATTERN.finditer(previous_text))
        for match in reversed(matches):
            candidate = previous_chunk.char_start + match.start()
            if (
                self._count_span(text, candidate, base_start)
                >= self.config.overlap_tokens
            ):
                break

        if candidate == base_start:
            return base_start
        if self._count_span(text, candidate, end) > self.config.max_chunk_tokens:
            return base_start
        return candidate


class ChunkingPipeline:
    """Persistencia de chunks para una `document_version` existente."""

    def __init__(
        self,
        session: Session,
        *,
        chunker: SemanticMarkdownChunker | None = None,
    ) -> None:
        self._session = session
        self._chunk_repo = ChunkRepository(session)
        self._document_repo = DocumentRepository(session)
        self._chunker = chunker or SemanticMarkdownChunker()

    def chunk_document_version(
        self,
        *,
        project_id: UUID,
        document_version_id: UUID,
    ) -> ChunkingRunResult:
        document_version = self._document_repo.get_version(
            project_id=project_id,
            document_version_id=document_version_id,
        )
        if document_version is None:
            raise ChunkingPipelineError("document version does not belong to project")

        existing_chunks = self._chunk_repo.list_by_document_version(
            project_id=project_id,
            document_version_id=document_version_id,
        )
        if existing_chunks:
            self._validate_existing_chunks(existing_chunks)
            return ChunkingRunResult(
                document_version=document_version,
                chunks=existing_chunks,
                created_chunks=False,
            )

        plans = self._chunker.chunk(document_version.normalized_text)
        chunks = [
            self._chunk_repo.create(
                project_id=project_id,
                document_version_id=document_version_id,
                ordinal=plan.ordinal,
                char_start=plan.char_start,
                char_end=plan.char_end,
                token_count=plan.token_count,
                section_metadata=plan.section_metadata,
                chunker_metadata=plan.chunker_metadata,
            )
            for plan in plans
        ]
        for index, chunk in enumerate(chunks):
            if index > 0:
                chunk.prev_chunk_id = chunks[index - 1].id
            if index < len(chunks) - 1:
                chunk.next_chunk_id = chunks[index + 1].id
        self._session.flush()
        return ChunkingRunResult(
            document_version=document_version,
            chunks=chunks,
            created_chunks=True,
        )

    def _validate_existing_chunks(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            metadata = chunk.chunker_metadata or {}
            if (
                metadata.get("chunker_version") != CHUNKER_VERSION
                or metadata.get("chunker_config_hash")
                != self._chunker.chunker_config_hash
            ):
                raise ChunkingPipelineError(
                    "document version already has chunks for another chunker config"
                )


def _split_lines(text: str) -> list[_Line]:
    lines: list[_Line] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        end = offset + len(line)
        lines.append(_Line(start=offset, end=end, text=line))
        offset = end
    if not lines:
        lines.append(_Line(start=0, end=len(text), text=text))
    return lines


def _is_blank(line: str) -> bool:
    return not line.strip()


def _consume_blank_lines(lines: list[_Line], index: int) -> int:
    while index < len(lines) and _is_blank(lines[index].text):
        index += 1
    return index


def _starts_code_fence(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("```") or stripped.startswith("~~~")


def _consume_code_fence(lines: list[_Line], index: int) -> int:
    fence = lines[index].text.lstrip()[:3]
    index += 1
    while index < len(lines):
        if lines[index].text.lstrip().startswith(fence):
            return index + 1
        index += 1
    return index


def _starts_table(lines: list[_Line], index: int) -> bool:
    if index + 1 >= len(lines):
        return False
    return "|" in lines[index].text and (
        _TABLE_SEPARATOR_PATTERN.match(lines[index + 1].text.strip()) is not None
    )


def _consume_table(lines: list[_Line], index: int) -> int:
    index += 1
    while index < len(lines) and "|" in lines[index].text:
        index += 1
    return index


def _consume_list(lines: list[_Line], index: int) -> int:
    while index < len(lines):
        line = lines[index].text
        if _is_blank(line):
            break
        if _LIST_PATTERN.match(line) is None and not line.startswith((" ", "\t")):
            break
        index += 1
    return index


def _consume_paragraph(lines: list[_Line], index: int) -> int:
    while index < len(lines):
        line = lines[index].text
        if _is_blank(line):
            break
        if index > 0 and (
            _HEADING_PATTERN.match(line.strip()) is not None
            or _starts_code_fence(line)
            or _LIST_PATTERN.match(line) is not None
            or _starts_table(lines, index)
        ):
            break
        index += 1
    return index


def _first_non_blank(blocks: list[_MarkdownBlock]) -> _MarkdownBlock:
    for block in blocks:
        if block.kind != "blank":
            return block
    return blocks[0]


def _hash_config(
    *,
    config: SemanticMarkdownChunkerConfig,
    token_estimator_name: str,
) -> str:
    payload = {
        "chunker_version": CHUNKER_VERSION,
        "config": config.as_metadata(),
        "token_estimator": token_estimator_name,
    }
    value = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"
