"""Run pgvector + BM25s hybrid search with reciprocal-rank fusion."""

from __future__ import annotations

import argparse
import json
import logging
import os
from contextlib import nullcontext
from time import perf_counter
from pathlib import Path
from typing import Any, Callable

import bm25s
import numpy as np
from bm25s.tokenization import Tokenizer
from sentence_transformers import SentenceTransformer

from .build_bm25s import DEFAULT_OUTPUT_DIR, TOKENIZER_SPLITTER
from .curriculum import group_results_by_curriculum, select_best_lesson
from .db import PgVectorStore, VECTOR_DIMENSIONS
from .rerank import (
    DEFAULT_RERANK_APP_NAME,
    DEFAULT_RERANK_MODEL,
    RERANK_MODEL_CLASSES,
    ModalRerankBackend,
    RerankBackend,
    rerank_candidates,
)
from .rerank_query import (
    DEFAULT_RERANK_METHOD_MIN_CONFIDENCE,
    DEFAULT_RERANK_QUERY_MODE,
    RERANK_QUERY_MODES,
    parse_query_context,
    select_rerank_query,
    validate_method_analysis,
)
from .rewrite import (
    DEFAULT_FORMULA_REWRITE_APP_NAME,
    DEFAULT_FORMULA_REWRITE_MODEL,
    FORMULA_REWRITE_MODEL_CLASSES,
    read_query_from_terminal,
    rewrite_query_views,
    spawn_query_rewrite_warmup,
)


DEFAULT_MODEL = "AITeamVN/Vietnamese_Embedding"
DEFAULT_CANDIDATE_K = 10
DEFAULT_RRF_K = 20
DEFAULT_RERANK_K = 10
MAX_RERANK_K = 10


def matches_filters(
    document: dict[str, Any],
    subject: str | None,
    grade: int | None,
    book_id: str | None,
) -> bool:
    metadata = document.get("metadata", {})
    return (
        (subject is None or metadata.get("subject") == subject)
        and (grade is None or metadata.get("grade") == grade)
        and (book_id is None or document.get("book_id") == book_id)
    )


def bm25_search(
    query: str,
    index_dir: Path,
    candidate_k: int,
    subject: str | None,
    grade: int | None,
    book_id: str | None,
) -> list[dict[str, Any]]:
    return Bm25SearchIndex(index_dir).search(
        query=query,
        candidate_k=candidate_k,
        subject=subject,
        grade=grade,
        book_id=book_id,
    )


class Bm25SearchIndex:
    """Loaded BM25s index that can be reused across multiple queries."""

    def __init__(self, index_dir: Path) -> None:
        self.index_dir = index_dir
        if not index_dir.is_dir():
            raise FileNotFoundError(
                f"BM25s index not found: {index_dir}. "
                "Run python -m rag.build_bm25s first."
            )

        self.tokenizer = Tokenizer(
            lower=True,
            splitter=TOKENIZER_SPLITTER,
            stopwords=[],
            stemmer=None,
        )
        self.tokenizer.load_vocab(index_dir)
        self.tokenizer.load_stopwords(index_dir)
        self.retriever = bm25s.BM25.load(index_dir, load_corpus=True, mmap=True)
        self.documents = self.retriever.corpus
        if self.documents is None:
            raise ValueError(f"BM25s corpus is missing from: {index_dir}")

    def search(
        self,
        query: str,
        candidate_k: int,
        subject: str | None,
        grade: int | None,
        book_id: str | None,
    ) -> list[dict[str, Any]]:
        documents = self.documents
        filter_mask = np.asarray(
            [matches_filters(document, subject, grade, book_id) for document in documents],
            dtype=np.float32,
        )
        if not filter_mask.any():
            return []

        query_tokens = self.tokenizer.tokenize([query], update_vocab=False)
        results, scores = self.retriever.retrieve(
            query_tokens,
            k=min(candidate_k, len(documents)),
            weight_mask=filter_mask,
            show_progress=False,
        )

        ranked_results: list[dict[str, Any]] = []
        for document, score in zip(results[0], scores[0]):
            document = dict(document)
            score = float(score)
            if score <= 0 or not matches_filters(document, subject, grade, book_id):
                continue
            ranked_results.append(
                {
                    "book_id": document["book_id"],
                    "section_id": document["section_id"],
                    "content": document["content"],
                    "metadata": document["metadata"],
                    "bm25_rank": len(ranked_results) + 1,
                    "bm25_score": score,
                }
            )
        return ranked_results


def rrf_fuse(
    vector_results: list[dict[str, Any]],
    bm25_results: list[dict[str, Any]],
    rrf_k: int,
) -> list[dict[str, Any]]:
    if rrf_k <= 0:
        raise ValueError("rrf_k must be positive")

    fused: dict[tuple[str, str], dict[str, Any]] = {}
    for result in vector_results:
        key = (result["book_id"], result["section_id"])
        fused[key] = {
            "book_id": result["book_id"],
            "section_id": result["section_id"],
            "content": result["content"],
            "metadata": result["metadata"],
            "vector_rank": int(result["vector_rank"]),
            "cosine_similarity": float(result["cosine_similarity"]),
            "bm25_rank": None,
            "bm25_score": None,
            "raw_rrf_score": 1.0 / (rrf_k + int(result["vector_rank"])),
        }

    for result in bm25_results:
        key = (result["book_id"], result["section_id"])
        contribution = 1.0 / (rrf_k + int(result["bm25_rank"]))
        existing = fused.get(key)
        if existing is None:
            fused[key] = {
                "book_id": result["book_id"],
                "section_id": result["section_id"],
                "content": result["content"],
                "metadata": result["metadata"],
                "vector_rank": None,
                "cosine_similarity": None,
                "bm25_rank": int(result["bm25_rank"]),
                "bm25_score": float(result["bm25_score"]),
                "raw_rrf_score": contribution,
            }
        else:
            existing["bm25_rank"] = int(result["bm25_rank"])
            existing["bm25_score"] = float(result["bm25_score"])
            existing["raw_rrf_score"] += contribution

    maximum_score = 2.0 / (rrf_k + 1)
    for result in fused.values():
        result["hybrid_score"] = result["raw_rrf_score"] / maximum_score

    return sorted(
        fused.values(),
        key=lambda result: (
            -result["raw_rrf_score"],
            result["book_id"],
            result["section_id"],
        ),
    )


def rrf_fuse_views(
    retrieval_runs: dict[
        str,
        tuple[list[dict[str, Any]], list[dict[str, Any]]],
    ],
    rrf_k: int,
) -> list[dict[str, Any]]:
    """Fuse vector and BM25 rankings from every enabled query view."""
    if rrf_k <= 0:
        raise ValueError("rrf_k must be positive")
    if not retrieval_runs:
        raise ValueError("retrieval_runs must not be empty")

    fused: dict[tuple[str, str], dict[str, Any]] = {}
    maximum_score = len(retrieval_runs) * 2.0 / (rrf_k + 1)

    for view_name, (vector_results, bm25_results) in retrieval_runs.items():
        for channel, results, rank_key, score_key in (
            ("vector", vector_results, "vector_rank", "cosine_similarity"),
            ("bm25", bm25_results, "bm25_rank", "bm25_score"),
        ):
            for result in results:
                key = (result["book_id"], result["section_id"])
                rank = int(result[rank_key])
                contribution = 1.0 / (rrf_k + rank)
                existing = fused.get(key)
                if existing is None:
                    existing = {
                        "book_id": result["book_id"],
                        "section_id": result["section_id"],
                        "content": result["content"],
                        "metadata": result["metadata"],
                        "query_ranks": {},
                        "query_rrf_contributions": {},
                        "raw_rrf_score": 0.0,
                    }
                    fused[key] = existing

                view_ranks = existing["query_ranks"].setdefault(view_name, {})
                view_ranks[f"{channel}_rank"] = rank
                view_ranks[score_key] = float(result[score_key])
                existing["query_rrf_contributions"][view_name] = (
                    existing["query_rrf_contributions"].get(view_name, 0.0)
                    + contribution
                )
                existing["raw_rrf_score"] += contribution

    for result in fused.values():
        result["hybrid_score"] = result["raw_rrf_score"] / maximum_score

    return sorted(
        fused.values(),
        key=lambda result: (
            -result["raw_rrf_score"],
            result["book_id"],
            result["section_id"],
        ),
    )


def _deduplicate_query_views(query_views: dict[str, str]) -> dict[str, str]:
    """Keep the first enabled view for each normalized query string."""
    deduplicated: dict[str, str] = {}
    seen: set[str] = set()
    for view_name, query in query_views.items():
        normalized = " ".join(query.split()).casefold()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduplicated[view_name] = query
    return deduplicated


class HybridSearcher:
    """Reusable hybrid search runtime for one or many queries."""

    def __init__(
        self,
        dsn: str,
        *,
        top_k: int = 5,
        candidate_k: int = DEFAULT_CANDIDATE_K,
        rrf_k: int = DEFAULT_RRF_K,
        original_query: bool = True,
        formula_rewrite: bool = True,
        method_rewrite: bool = False,
        formula_rewrite_app_name: str = DEFAULT_FORMULA_REWRITE_APP_NAME,
        formula_rewrite_model: str = DEFAULT_FORMULA_REWRITE_MODEL,
        formula_rewrite_class_name: str | None = None,
        formula_rewrite_modal_logs: bool = False,
        rerank: bool = True,
        rerank_k: int = DEFAULT_RERANK_K,
        rerank_query_mode: str = DEFAULT_RERANK_QUERY_MODE,
        rerank_method_min_confidence: float = DEFAULT_RERANK_METHOD_MIN_CONFIDENCE,
        rerank_app_name: str = DEFAULT_RERANK_APP_NAME,
        rerank_model: str = DEFAULT_RERANK_MODEL,
        rerank_class_name: str | None = None,
        rerank_modal_logs: bool = False,
        rerank_backend: RerankBackend | None = None,
        model_name: str = DEFAULT_MODEL,
        device: str | None = None,
        subject: str | None = None,
        grade: int | None = None,
        book_id: str | None = None,
        bm25_index: Path = DEFAULT_OUTPUT_DIR,
        logger: logging.Logger | None = None,
    ) -> None:
        if not dsn:
            raise ValueError("Set RAG_DATABASE_URL or pass --dsn")
        if top_k <= 0 or candidate_k <= 0 or rrf_k <= 0 or rerank_k <= 0:
            raise ValueError("top_k, candidate_k, rrf_k, and rerank_k must be positive")
        if rerank_k > MAX_RERANK_K:
            raise ValueError(f"rerank_k must not exceed {MAX_RERANK_K}")
        if rerank_query_mode not in RERANK_QUERY_MODES:
            raise ValueError(
                "rerank_query_mode must be one of: " + ", ".join(RERANK_QUERY_MODES)
            )
        if not 0.0 <= rerank_method_min_confidence <= 1.0:
            raise ValueError("rerank_method_min_confidence must be within [0, 1]")
        if not original_query and not formula_rewrite and not method_rewrite:
            raise ValueError("enable original_query, formula_rewrite, or method_rewrite")

        self.top_k = top_k
        self.candidate_k = candidate_k
        self.rrf_k = rrf_k
        self.rerank_k = rerank_k
        self.rerank_query_mode = rerank_query_mode
        self.rerank_method_min_confidence = rerank_method_min_confidence
        self.original_query_enabled = original_query
        self.formula_rewrite_enabled = formula_rewrite
        self.method_rewrite_enabled = method_rewrite
        self.formula_rewrite_app_name = formula_rewrite_app_name
        self.formula_rewrite_model = formula_rewrite_model
        self.formula_rewrite_class_name = formula_rewrite_class_name
        self.formula_rewrite_modal_logs = formula_rewrite_modal_logs
        self.rerank_enabled = rerank
        self.rerank_model = rerank_model if rerank else None
        self.rerank_backend = rerank_backend
        if rerank and self.rerank_backend is None:
            self.rerank_backend = ModalRerankBackend(
                app_name=rerank_app_name,
                class_name=rerank_class_name,
                model=rerank_model,
                show_modal_logs=rerank_modal_logs,
            )
        self.subject = subject
        self.grade = grade
        self.book_id = book_id
        self.logger = logger

        if logger is not None:
            logger.info("Original query view: %s", "bật" if original_query else "tắt")
            if formula_rewrite:
                logger.info(
                    "Formula rewrite đang bật: model=%s, class=%s, modal_logs=%s",
                    formula_rewrite_model,
                    formula_rewrite_class_name or "tự động",
                    formula_rewrite_modal_logs,
                )
            else:
                logger.info("Formula rewrite đang tắt")
            logger.info("Method rewrite: %s", "bật" if method_rewrite else "tắt")
            if rerank:
                logger.info(
                    "Rerank đang bật: model=%s, class=%s, modal_logs=%s",
                    rerank_model,
                    rerank_class_name or "tự động",
                    rerank_modal_logs,
                )
                logger.info(
                    "Rerank query: mode=%s, method_min_confidence=%.2f",
                    rerank_query_mode,
                    rerank_method_min_confidence,
                )
            else:
                logger.info("Rerank đang tắt")

        if logger is not None:
            logger.info("Đang nạp embedding model: %s", model_name)
        self.model = SentenceTransformer(model_name, device=device)
        self.model.max_seq_length = 2048
        if logger is not None:
            logger.info("Đã nạp embedding model")

        resolved_bm25_index = bm25_index.resolve()
        if logger is not None:
            logger.info("Đang nạp BM25 index: %s", resolved_bm25_index)
        self.bm25_index = Bm25SearchIndex(resolved_bm25_index)
        if logger is not None:
            logger.info("Đã nạp BM25 index")

        if logger is not None:
            logger.info("Đang cấu hình kết nối pgvector")
        self.store = PgVectorStore(dsn)
        if logger is not None:
            logger.info("Hybrid search đã sẵn sàng")

    def warmup_modal_models_concurrently(self) -> bool:
        """Load rewrite and rerank models concurrently when both are enabled."""
        rewrite_enabled = self.formula_rewrite_enabled or self.method_rewrite_enabled
        if not rewrite_enabled or not self.rerank_enabled:
            return False
        spawn_rerank_warmup = getattr(self.rerank_backend, "spawn_warmup", None)
        if not callable(spawn_rerank_warmup):
            raise RuntimeError("Configured rerank backend does not support Modal warmup")

        try:
            import modal
        except ImportError as error:
            raise RuntimeError(
                "Missing dependency 'modal'. Install ai-engine/rag/requirements.txt first."
            ) from error

        if self.logger is not None:
            self.logger.info("Đang khởi động đồng thời model rewrite và rerank trên Modal")
        started_at = perf_counter()
        show_modal_logs = self.formula_rewrite_modal_logs or bool(
            getattr(self.rerank_backend, "show_modal_logs", False)
        )
        output_context = modal.enable_output() if show_modal_logs else nullcontext()
        with output_context:
            rewrite_call = spawn_query_rewrite_warmup(
                app_name=self.formula_rewrite_app_name,
                class_name=self.formula_rewrite_class_name,
                model=self.formula_rewrite_model,
            )
            rerank_call = spawn_rerank_warmup()
            rewrite_result = rewrite_call.get()
            rerank_result = rerank_call.get()

        if self.logger is not None:
            self.logger.info(
                "Hai model Modal đã sẵn sàng trong %.2fs: rewrite=%s, rerank=%s",
                perf_counter() - started_at,
                rewrite_result.get("model") if isinstance(rewrite_result, dict) else "ready",
                rerank_result.get("model") if isinstance(rerank_result, dict) else "ready",
            )
        return True

    @staticmethod
    def _notify(
        progress_callback: Callable[[str], None] | None,
        stage: str,
    ) -> None:
        if progress_callback is not None:
            progress_callback(stage)

    def classify(
        self,
        query: str,
        *,
        debug: bool = False,
        debug_candidate_count: int | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Classify one query while reusing the loaded model and BM25 index."""
        if not query.strip():
            raise ValueError("query must not be empty")

        total_started_at = perf_counter()
        original_query = query
        query_context = parse_query_context(original_query)
        rewrite_result: dict[str, object] | None = None
        formula_query: str | None = None
        formula_concepts: list[object] = []
        formula_used_fallback = False
        formula_fallback_reason: object | None = None
        method_query: str | None = None
        method_analysis: dict[str, Any] | None = None
        method_analysis_validation_reason: str | None = None
        method_confidence: float | None = None
        method_used_fallback = False
        method_fallback_reason: object | None = None
        query_rewrite_seconds = 0.0
        formula_rewrite_seconds = 0.0
        method_rewrite_seconds = 0.0

        rewrite_enabled = self.formula_rewrite_enabled or self.method_rewrite_enabled
        if rewrite_enabled:
            if self.formula_rewrite_enabled:
                self._notify(progress_callback, "formula_rewrite_started")
            if self.method_rewrite_enabled:
                self._notify(progress_callback, "method_rewrite_started")
            rewrite_started_at = perf_counter()
            rewrite_result = rewrite_query_views(
                original_query,
                formula_rewrite=self.formula_rewrite_enabled,
                method_rewrite=self.method_rewrite_enabled,
                app_name=self.formula_rewrite_app_name,
                class_name=self.formula_rewrite_class_name,
                model=self.formula_rewrite_model,
                show_modal_logs=self.formula_rewrite_modal_logs,
            )
            query_rewrite_seconds = perf_counter() - rewrite_started_at
            rewrite_timings = rewrite_result.get("rewrite_timings_seconds", {})
            if isinstance(rewrite_timings, dict):
                formula_rewrite_seconds = float(rewrite_timings.get("formula", 0.0))
                method_rewrite_seconds = float(rewrite_timings.get("method", 0.0))

            if self.formula_rewrite_enabled:
                rewritten_formula = rewrite_result.get("formula_query")
                if not isinstance(rewritten_formula, str) or not rewritten_formula.strip():
                    raise ValueError("Modal rewrite response is missing formula_query")
                formula_query = rewritten_formula.strip()
            returned_concepts = rewrite_result.get("formula_concepts", [])
            if isinstance(returned_concepts, list):
                formula_concepts = returned_concepts
            formula_used_fallback = bool(
                rewrite_result.get("formula_used_fallback", False)
            )
            formula_fallback_reason = rewrite_result.get("formula_fallback_reason")

            returned_method_query = rewrite_result.get("method_query")
            if isinstance(returned_method_query, str) and returned_method_query.strip():
                method_query = returned_method_query.strip()
            returned_method_analysis = rewrite_result.get("method_analysis")
            if returned_method_analysis is not None:
                method_analysis, method_analysis_validation_reason = (
                    validate_method_analysis(returned_method_analysis)
                )
            returned_method_confidence = rewrite_result.get("method_confidence")
            if isinstance(returned_method_confidence, (int, float)):
                method_confidence = float(returned_method_confidence)
            method_used_fallback = bool(
                rewrite_result.get("method_used_fallback", False)
            )
            method_fallback_reason = rewrite_result.get("method_fallback_reason")
            if self.formula_rewrite_enabled:
                self._notify(progress_callback, "formula_rewrite_completed")
            if self.method_rewrite_enabled:
                self._notify(progress_callback, "method_rewrite_completed")

        rerank_query_selection = select_rerank_query(
            original_query=original_query,
            context=query_context,
            requested_mode=self.rerank_query_mode,
            method_rewrite_enabled=self.method_rewrite_enabled,
            method_analysis=method_analysis,
            method_confidence=method_confidence,
            method_used_fallback=method_used_fallback,
            min_confidence=self.rerank_method_min_confidence,
        )

        requested_query_views: dict[str, str] = {}
        if self.original_query_enabled:
            requested_query_views["original"] = original_query
        if self.formula_rewrite_enabled and formula_query is not None:
            requested_query_views["formula"] = formula_query
        if self.method_rewrite_enabled and method_query is not None:
            requested_query_views["method"] = method_query
        query_views = _deduplicate_query_views(requested_query_views)
        if not query_views:
            raise RuntimeError(
                "No usable query view was produced; enabled rewrite view may have failed"
            )

        self._notify(progress_callback, "search_started")
        vectorize_started_at = perf_counter()
        view_names = list(query_views)
        query_embeddings = self.model.encode(
            [query_views[name] for name in view_names],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        for query_embedding in query_embeddings:
            if len(query_embedding) != VECTOR_DIMENSIONS:
                raise ValueError(
                    f"Expected {VECTOR_DIMENSIONS} embedding dimensions, "
                    f"got {len(query_embedding)}"
                )
        vectorize_seconds = perf_counter() - vectorize_started_at

        retrieval_started_at = perf_counter()
        retrieval_runs: dict[
            str,
            tuple[list[dict[str, Any]], list[dict[str, Any]]],
        ] = {}
        for view_name, query_embedding in zip(
            view_names, query_embeddings, strict=True
        ):
            vector_results = self.store.vector_search(
                query_embedding=query_embedding.tolist(),
                match_count=self.candidate_k,
                subject=self.subject,
                grade=self.grade,
                book_id=self.book_id,
            )
            lexical_results = self.bm25_index.search(
                query=query_views[view_name],
                candidate_k=self.candidate_k,
                subject=self.subject,
                grade=self.grade,
                book_id=self.book_id,
            )
            retrieval_runs[view_name] = (vector_results, lexical_results)
        fused_sections = rrf_fuse_views(retrieval_runs, self.rrf_k)
        retrieval_seconds = perf_counter() - retrieval_started_at
        self._notify(progress_callback, "search_completed")

        rerank_seconds = 0.0
        if self.rerank_enabled and fused_sections:
            if self.rerank_backend is None:
                raise RuntimeError("Rerank is enabled but no backend is configured")
            self._notify(progress_callback, "rerank_started")
            rerank_started_at = perf_counter()
            rerank_input = fused_sections[: self.rerank_k]
            reranked_sections = rerank_candidates(
                rerank_query_selection.query,
                rerank_input,
                self.rerank_backend,
            )
            fused_sections = reranked_sections + fused_sections[self.rerank_k :]
            rerank_seconds = perf_counter() - rerank_started_at
            self._notify(progress_callback, "rerank_completed")
        ranked_sections = fused_sections[: self.top_k]

        if not debug:
            return select_best_lesson(ranked_sections)

        if debug_candidate_count is not None and debug_candidate_count <= 0:
            raise ValueError("debug_candidate_count must be positive")
        debug_limit = debug_candidate_count or self.top_k
        debug_sections = fused_sections[:debug_limit]
        candidates: list[dict[str, Any]] = []
        for rank, section in enumerate(debug_sections, start=1):
            lesson = select_best_lesson([section])
            candidates.append(
                {
                    "rank": rank,
                    "Grade": lesson["Grade"],
                    "Chapter": lesson["Chapter"],
                    "Lesson": lesson["Lesson"],
                    **section,
                }
            )

        return {
            "classification": select_best_lesson(ranked_sections),
            "original_query": original_query,
            "original_query_enabled": self.original_query_enabled,
            "formula_rewrite_enabled": self.formula_rewrite_enabled,
            "formula_query": formula_query,
            "formula_concepts": formula_concepts,
            "formula_used_fallback": formula_used_fallback,
            "formula_fallback_reason": formula_fallback_reason,
            "method_rewrite_enabled": self.method_rewrite_enabled,
            "method_query": method_query,
            "method_analysis": method_analysis,
            "method_analysis_validation_reason": method_analysis_validation_reason,
            "method_confidence": method_confidence,
            "method_used_fallback": method_used_fallback,
            "method_fallback_reason": method_fallback_reason,
            "query_context": query_context.as_debug_dict(),
            "rerank_query_mode_requested": rerank_query_selection.requested_mode,
            "rerank_query_mode_effective": rerank_query_selection.effective_mode,
            "rerank_query": rerank_query_selection.query,
            "rerank_query_used_fallback": rerank_query_selection.used_fallback,
            "rerank_query_fallback_reason": rerank_query_selection.fallback_reason,
            "query_views": query_views,
            "retrieval_runs": {
                view_name: {
                    "query": query_views[view_name],
                    "vector_count": len(vector_results),
                    "bm25_count": len(bm25_results),
                }
                for view_name, (vector_results, bm25_results) in retrieval_runs.items()
            },
            "rerank_model": self.rerank_model,
            "candidate_count": len(candidates),
            "candidates": candidates,
            "timings_seconds": {
                "query_rewrite": round(query_rewrite_seconds, 3),
                "formula_rewrite": round(formula_rewrite_seconds, 3),
                "method_rewrite": round(method_rewrite_seconds, 3),
                "vectorize": round(vectorize_seconds, 3),
                "retrieval": round(retrieval_seconds, 3),
                "rerank": round(rerank_seconds, 3),
                "total": round(perf_counter() - total_started_at, 3),
            },
            "results": group_results_by_curriculum(debug_sections),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=5, help="Final ranked results")
    parser.add_argument(
        "--candidate-k",
        type=int,
        default=DEFAULT_CANDIDATE_K,
        help="Candidates from each retriever before RRF; default: 10",
    )
    parser.add_argument("--rrf-k", type=int, default=DEFAULT_RRF_K)
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Return the full retrieval, ranking, and timing payload instead of one lesson.",
    )
    parser.add_argument(
        "--original-query",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Retrieve with the untouched original query (default: enabled)",
    )
    parser.add_argument(
        "--formula-rewrite",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Retrieve with parser-owned formula descriptions (default: enabled)",
    )
    parser.add_argument(
        "--method-rewrite",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Retrieve with one inferred method query (default: disabled)",
    )
    parser.add_argument(
        "--formula-rewrite-app-name",
        default=DEFAULT_FORMULA_REWRITE_APP_NAME,
        help="Modal app that hosts formula and method rewrite tasks",
    )
    parser.add_argument(
        "--formula-rewrite-model",
        choices=FORMULA_REWRITE_MODEL_CLASSES,
        default=DEFAULT_FORMULA_REWRITE_MODEL,
        help="Modal formula/method rewrite model; default: qwen3-14b-awq",
    )
    parser.add_argument(
        "--formula-rewrite-class-name",
        default=None,
        help="Override the Modal class selected by --formula-rewrite-model",
    )
    parser.add_argument(
        "--formula-rewrite-modal-logs",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Stream formula/method rewrite worker output to this terminal",
    )
    parser.add_argument(
        "--rerank",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Rerank fused candidates through Modal (default: enabled)",
    )
    parser.add_argument(
        "--rerank-k",
        type=int,
        default=DEFAULT_RERANK_K,
        help="RRF candidates sent to reranker; default: 10",
    )
    parser.add_argument(
        "--rerank-query-mode",
        choices=RERANK_QUERY_MODES,
        default=DEFAULT_RERANK_QUERY_MODE,
        help="Query supplied to reranker; default: original",
    )
    parser.add_argument(
        "--rerank-method-min-confidence",
        type=float,
        default=DEFAULT_RERANK_METHOD_MIN_CONFIDENCE,
        help="Structured mode falls back below this method confidence; default: 0.7",
    )
    parser.add_argument(
        "--rerank-app-name",
        default=DEFAULT_RERANK_APP_NAME,
        help="Modal app name for --rerank",
    )
    parser.add_argument(
        "--rerank-model",
        choices=RERANK_MODEL_CLASSES,
        default=DEFAULT_RERANK_MODEL,
        help=f"Modal rerank model; default: {DEFAULT_RERANK_MODEL}",
    )
    parser.add_argument(
        "--rerank-class-name",
        default=None,
        help="Override the Modal class selected by --rerank-model",
    )
    parser.add_argument(
        "--rerank-modal-logs",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Stream Modal rerank worker output to this terminal",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--device", default=None, help="cpu, cuda, or omit for auto")
    parser.add_argument("--subject")
    parser.add_argument("--grade", type=int)
    parser.add_argument("--book-id")
    parser.add_argument(
        "--bm25-index",
        type=Path,
        default=Path(os.getenv("RAG_BM25_INDEX_DIR", DEFAULT_OUTPUT_DIR)),
        help=f"Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--dsn",
        default=os.getenv("RAG_DATABASE_URL"),
        help="PostgreSQL DSN; defaults to RAG_DATABASE_URL",
    )
    args = parser.parse_args()

    if not args.dsn:
        parser.error("Set RAG_DATABASE_URL or pass --dsn")
    if not args.original_query and not args.formula_rewrite and not args.method_rewrite:
        parser.error("enable --original-query, --formula-rewrite, or --method-rewrite")
    if (
        args.top_k <= 0
        or args.candidate_k <= 0
        or args.rrf_k <= 0
        or args.rerank_k <= 0
    ):
        parser.error("--top-k, --candidate-k, --rrf-k, and --rerank-k must be positive")
    if args.rerank_k > MAX_RERANK_K:
        parser.error(f"--rerank-k must not exceed {MAX_RERANK_K}")
    if not 0.0 <= args.rerank_method_min_confidence <= 1.0:
        parser.error("--rerank-method-min-confidence must be within [0, 1]")

    try:
        original_query = read_query_from_terminal()
    except ValueError as error:
        parser.error(str(error))

    try:
        searcher = HybridSearcher(
            args.dsn,
            top_k=args.top_k,
            candidate_k=args.candidate_k,
            rrf_k=args.rrf_k,
            original_query=args.original_query,
            formula_rewrite=args.formula_rewrite,
            method_rewrite=args.method_rewrite,
            formula_rewrite_app_name=args.formula_rewrite_app_name,
            formula_rewrite_model=args.formula_rewrite_model,
            formula_rewrite_class_name=args.formula_rewrite_class_name,
            formula_rewrite_modal_logs=args.formula_rewrite_modal_logs,
            rerank=args.rerank,
            rerank_k=args.rerank_k,
            rerank_query_mode=args.rerank_query_mode,
            rerank_method_min_confidence=args.rerank_method_min_confidence,
            rerank_app_name=args.rerank_app_name,
            rerank_model=args.rerank_model,
            rerank_class_name=args.rerank_class_name,
            rerank_modal_logs=args.rerank_modal_logs,
            model_name=args.model,
            device=args.device,
            subject=args.subject,
            grade=args.grade,
            book_id=args.book_id,
            bm25_index=args.bm25_index,
        )
        result = searcher.classify(original_query, debug=args.debug)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
