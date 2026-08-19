"""Build a focused, method-aware query for post-retrieval reranking."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


RERANK_QUERY_MODES = ("original", "structured")
DEFAULT_RERANK_QUERY_MODE = "original"
DEFAULT_RERANK_METHOD_MIN_CONFIDENCE = 0.7
PART_PATTERN = re.compile(r"^\s*(?P<part>[a-z])\s*\)")

_METHOD_FIELD_WORD_LIMITS = {
    "target": 20,
    "transformation": 30,
    "method": 16,
}
_TAXONOMY_LABEL_RE = re.compile(
    r"\b(?:lesson_id|chapter_id|section_id|topic_id)\b"
    r"|\b(?:Grade|Chapter|Lesson)\s*:"
    r"|\b(?:Chương|Bài)\s+\d+\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class QueryContext:
    """Parser-owned view of the active exam subquestion."""

    original_query: str
    stem: str
    part: str | None
    focused_subquestion: str
    used_fallback: bool = False
    fallback_reason: str | None = None

    def as_debug_dict(self) -> dict[str, Any]:
        return {
            "part": self.part,
            "focused_subquestion": self.focused_subquestion,
            "focus_used_fallback": self.used_fallback,
            "focus_fallback_reason": self.fallback_reason,
        }


@dataclass(frozen=True)
class RerankQuerySelection:
    requested_mode: str
    effective_mode: str
    query: str
    used_fallback: bool = False
    fallback_reason: str | None = None


def parse_query_context(query: str) -> QueryContext:
    """Select one line-start a)/b)/c)/d-style subquestion without rewriting it."""
    original_query = query.strip()
    if not original_query:
        raise ValueError("query must not be empty")

    lines = original_query.splitlines()
    part_starts = [
        (index, match.group("part").lower())
        for index, line in enumerate(lines)
        if (match := PART_PATTERN.match(line)) is not None
    ]
    if not part_starts:
        return QueryContext(
            original_query=original_query,
            stem="",
            part=None,
            focused_subquestion=original_query,
        )
    if len(part_starts) > 1:
        return QueryContext(
            original_query=original_query,
            stem="",
            part=None,
            focused_subquestion=original_query,
            used_fallback=True,
            fallback_reason="multiple subquestions are present in one query",
        )

    start, part = part_starts[0]
    focused_subquestion = "\n".join(lines[start:]).strip()
    if not focused_subquestion:
        return QueryContext(
            original_query=original_query,
            stem="",
            part=None,
            focused_subquestion=original_query,
            used_fallback=True,
            fallback_reason="focused subquestion is empty",
        )
    return QueryContext(
        original_query=original_query,
        stem="\n".join(lines[:start]).strip(),
        part=part,
        focused_subquestion=focused_subquestion,
    )


def _contains_latex(value: str) -> bool:
    if "$" in value:
        return True
    return any(
        character == "\\"
        and position + 1 < len(value)
        and (value[position + 1].isalpha() or value[position + 1] in "()[]")
        for position, character in enumerate(value)
    )


def _validated_text(value: Any, field: str, max_words: int) -> tuple[str, str | None]:
    if not isinstance(value, str):
        return "", f"{field} is not a string"
    text = value.strip()
    if not text:
        return "", f"{field} is empty"
    if len(text.split()) > max_words:
        return "", f"{field} exceeds {max_words} words"
    if _contains_latex(text):
        return "", f"{field} contains LaTeX"
    if _TAXONOMY_LABEL_RE.search(text):
        return "", f"{field} contains a taxonomy label"
    return text, None


def validate_method_analysis(
    value: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    """Validate remote method fields again before they influence reranking."""
    if not isinstance(value, Mapping):
        return None, "method analysis is not an object"

    expected_fields = {"relevant_givens", *_METHOD_FIELD_WORD_LIMITS}
    unexpected_fields = set(value) - expected_fields
    if unexpected_fields:
        return (
            None,
            "method analysis has unexpected fields: "
            + ", ".join(sorted(unexpected_fields)),
        )

    givens_value = value.get("relevant_givens")
    if not isinstance(givens_value, list):
        return None, "relevant_givens is not an array"
    if not 1 <= len(givens_value) <= 5:
        return None, "relevant_givens must contain 1 to 5 items"

    relevant_givens: list[str] = []
    for index, given_value in enumerate(givens_value, start=1):
        given, reason = _validated_text(
            given_value,
            f"relevant_givens[{index}]",
            16,
        )
        if reason is not None:
            return None, reason
        relevant_givens.append(given)

    analysis: dict[str, Any] = {"relevant_givens": relevant_givens}
    for field, max_words in _METHOD_FIELD_WORD_LIMITS.items():
        text, reason = _validated_text(value.get(field), field, max_words)
        if reason is not None:
            return None, reason
        analysis[field] = text
    return analysis, None


def build_structured_rerank_query(
    context: QueryContext,
    method_analysis: Any,
) -> str:
    """Render validated open-text method analysis without generating taxonomy labels."""
    analysis, reason = validate_method_analysis(method_analysis)
    if analysis is None:
        raise ValueError(reason or "method analysis is invalid")

    givens = "\n".join(
        f"- {given}" for given in analysis["relevant_givens"]
    )
    return (
        "Câu hỏi cần phân loại:\n"
        f"{context.focused_subquestion}\n\n"
        "Dữ kiện liên quan:\n"
        f"{givens}\n\n"
        "Mục tiêu cần xác định:\n"
        f"{analysis['target']}\n\n"
        "Hướng biến đổi:\n"
        f"{analysis['transformation']}\n\n"
        "Phương pháp trực tiếp cần dùng:\n"
        f"{analysis['method']}"
    )


def select_rerank_query(
    *,
    original_query: str,
    context: QueryContext,
    requested_mode: str,
    method_rewrite_enabled: bool,
    method_analysis: Any,
    method_confidence: Any,
    method_used_fallback: bool,
    min_confidence: float,
) -> RerankQuerySelection:
    """Choose structured reranking only when every required signal is valid."""
    if requested_mode not in RERANK_QUERY_MODES:
        raise ValueError(
            "requested_mode must be one of: " + ", ".join(RERANK_QUERY_MODES)
        )
    if not 0.0 <= min_confidence <= 1.0:
        raise ValueError("min_confidence must be within [0, 1]")
    if requested_mode == "original":
        return RerankQuerySelection("original", "original", original_query)

    fallback_reason: str | None = None
    if not method_rewrite_enabled:
        fallback_reason = "method rewrite is disabled"
    elif context.used_fallback:
        fallback_reason = context.fallback_reason or "query focus is ambiguous"
    elif method_used_fallback:
        fallback_reason = "method rewrite used fallback"
    elif isinstance(method_confidence, bool) or not isinstance(
        method_confidence, (int, float)
    ):
        fallback_reason = "method confidence is unavailable"
    elif not 0.0 <= float(method_confidence) <= 1.0:
        fallback_reason = "method confidence is outside [0, 1]"
    elif float(method_confidence) < min_confidence:
        fallback_reason = (
            f"method confidence {float(method_confidence):.3f} is below "
            f"{min_confidence:.3f}"
        )

    if fallback_reason is None:
        try:
            structured_query = build_structured_rerank_query(
                context,
                method_analysis,
            )
        except ValueError as error:
            fallback_reason = str(error)
        else:
            return RerankQuerySelection(
                requested_mode="structured",
                effective_mode="structured",
                query=structured_query,
            )

    return RerankQuerySelection(
        requested_mode="structured",
        effective_mode="original",
        query=original_query,
        used_fallback=True,
        fallback_reason=fallback_reason,
    )
