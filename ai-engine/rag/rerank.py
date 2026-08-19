"""Model-agnostic reranking for hybrid retrieval candidates."""

from __future__ import annotations

import math
from typing import Any, Protocol, Sequence


DEFAULT_RERANK_APP_NAME = "exam-rag-qwen3-rerank"
DEFAULT_RERANK_CLASS_NAME = "Qwen3Reranker4B"
DEFAULT_RERANK_MODEL = "qwen3-reranker-4b"
RERANK_MODEL_CLASSES = {
    DEFAULT_RERANK_MODEL: DEFAULT_RERANK_CLASS_NAME,
    "qwen3-reranker-0.6b": "Qwen3Reranker06B",
}


class RerankBackend(Protocol):
    """Score query-document pairs without owning retrieval behavior."""

    def score(self, query: str, documents: Sequence[str]) -> list[float]: ...


def rerank_class_name(model: str) -> str:
    """Resolve a user-facing model name to its deployed Modal class."""
    try:
        return RERANK_MODEL_CLASSES[model]
    except KeyError as error:
        choices = ", ".join(RERANK_MODEL_CLASSES)
        raise ValueError(f"Unknown rerank model {model!r}; choose one of: {choices}") from error


class ModalRerankBackend:
    """Rerank through a deployed Modal worker selected from the model registry."""

    def __init__(
        self,
        *,
        app_name: str = DEFAULT_RERANK_APP_NAME,
        class_name: str | None = None,
        model: str = DEFAULT_RERANK_MODEL,
        show_modal_logs: bool = False,
    ) -> None:
        self.app_name = app_name
        self.class_name = class_name or rerank_class_name(model)
        self.model = model
        self.show_modal_logs = show_modal_logs

    def score(self, query: str, documents: Sequence[str]) -> list[float]:
        if not query.strip():
            raise ValueError("rerank query must not be empty")
        if not documents:
            return []

        try:
            import modal
        except ImportError as error:
            raise RuntimeError(
                "Missing dependency 'modal'. Install ai-engine/rag/requirements.txt first."
            ) from error

        reranker_class = modal.Cls.from_name(self.app_name, self.class_name)
        if self.show_modal_logs:
            with modal.enable_output():
                response = reranker_class().rerank.remote(query, list(documents))
        else:
            response = reranker_class().rerank.remote(query, list(documents))

        if not isinstance(response, dict):
            raise ValueError("Modal reranker response must be an object")
        scores = response.get("scores")
        if not isinstance(scores, list):
            raise ValueError("Modal reranker response is missing scores")
        return _validated_scores(scores, len(documents))

    def spawn_warmup(self) -> object:
        """Start a non-blocking Modal call that loads the rerank model."""
        try:
            import modal
        except ImportError as error:
            raise RuntimeError(
                "Missing dependency 'modal'. Install ai-engine/rag/requirements.txt first."
            ) from error

        reranker_class = modal.Cls.from_name(self.app_name, self.class_name)
        return reranker_class().warmup.spawn()

    def release(self) -> dict[str, object]:
        """Release the remote reranker model after the batch has finished."""
        try:
            import modal
        except ImportError as error:
            raise RuntimeError(
                "Missing dependency 'modal'. Install ai-engine/rag/requirements.txt first."
            ) from error

        reranker_class = modal.Cls.from_name(self.app_name, self.class_name)
        response = reranker_class().release.remote()
        if not isinstance(response, dict):
            raise ValueError("Modal reranker release response must be an object")
        return response


def _validated_scores(values: Sequence[Any], expected_count: int) -> list[float]:
    if len(values) != expected_count:
        raise ValueError(
            f"Reranker returned {len(values)} scores for {expected_count} documents"
        )

    scores: list[float] = []
    for index, value in enumerate(values):
        if isinstance(value, bool):
            raise ValueError(f"Reranker score {index} is not numeric")
        try:
            score = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Reranker score {index} is not numeric") from error
        if not math.isfinite(score):
            raise ValueError(f"Reranker score {index} is not finite")
        scores.append(score)
    return scores


def rerank_candidates(
    query: str,
    candidates: Sequence[dict[str, Any]],
    backend: RerankBackend,
) -> list[dict[str, Any]]:
    """Return copied candidates ordered by model score, with RRF tie-breaking."""
    if not query.strip():
        raise ValueError("rerank query must not be empty")
    if not candidates:
        return []

    documents: list[str] = []
    for index, candidate in enumerate(candidates):
        content = candidate.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"Rerank candidate {index} has no content")
        documents.append(content)

    scores = _validated_scores(backend.score(query, documents), len(candidates))
    scored = [
        ({**candidate, "rerank_score": score}, original_rank)
        for original_rank, (candidate, score) in enumerate(
            zip(candidates, scores, strict=True),
            start=1,
        )
    ]
    scored.sort(key=lambda item: (-item[0]["rerank_score"], item[1]))

    reranked: list[dict[str, Any]] = []
    for rerank_rank, (candidate, _) in enumerate(scored, start=1):
        candidate["rerank_rank"] = rerank_rank
        reranked.append(candidate)
    return reranked
