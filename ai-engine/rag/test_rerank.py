"""Focused tests for the model-agnostic reranking contract."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from .rerank import ModalRerankBackend, rerank_candidates, rerank_class_name


class _FixedBackend:
    def __init__(self, scores):
        self.scores = scores
        self.calls = []

    def score(self, query, documents):
        self.calls.append((query, list(documents)))
        return self.scores


class RerankTests(unittest.TestCase):
    def test_default_model_resolves_to_deployed_class(self) -> None:
        self.assertEqual(
            rerank_class_name("qwen3-reranker-4b"),
            "Qwen3Reranker4B",
        )
        backend = ModalRerankBackend()
        self.assertEqual(backend.class_name, "Qwen3Reranker4B")

    def test_smaller_model_remains_selectable(self) -> None:
        self.assertEqual(
            rerank_class_name("qwen3-reranker-0.6b"),
            "Qwen3Reranker06B",
        )
        backend = ModalRerankBackend(model="qwen3-reranker-0.6b")
        self.assertEqual(backend.class_name, "Qwen3Reranker06B")

    def test_unknown_model_fails_before_remote_call(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown rerank model"):
            ModalRerankBackend(model="unknown")

    def test_modal_backend_uses_selected_app_and_class(self) -> None:
        modal_module = MagicMock()
        modal_module.Cls.from_name.return_value.return_value.rerank.remote.return_value = {
            "model": "Qwen/Qwen3-Reranker-0.6B",
            "scores": [0.25, -1.5],
        }
        backend = ModalRerankBackend(
            app_name="rerank-app",
            class_name="ReplacementReranker",
            model="replacement",
        )

        with patch.dict("sys.modules", {"modal": modal_module}):
            scores = backend.score("query", ["first", "second"])

        self.assertEqual(scores, [0.25, -1.5])
        modal_module.Cls.from_name.assert_called_once_with(
            "rerank-app",
            "ReplacementReranker",
        )
        remote = modal_module.Cls.from_name.return_value.return_value.rerank.remote
        remote.assert_called_once_with("query", ["first", "second"])

    def test_modal_backend_can_spawn_non_blocking_warmup(self) -> None:
        modal_module = MagicMock()
        expected_call = object()
        modal_module.Cls.from_name.return_value.return_value.warmup.spawn.return_value = (
            expected_call
        )
        backend = ModalRerankBackend(
            app_name="rerank-app",
            class_name="ReplacementReranker",
            model="replacement",
        )

        with patch.dict("sys.modules", {"modal": modal_module}):
            call = backend.spawn_warmup()

        self.assertIs(call, expected_call)
        modal_module.Cls.from_name.assert_called_once_with(
            "rerank-app",
            "ReplacementReranker",
        )
        spawn = modal_module.Cls.from_name.return_value.return_value.warmup.spawn
        spawn.assert_called_once_with()

    def test_candidates_are_copied_and_sorted_by_score(self) -> None:
        candidates = [
            {"section_id": "first", "content": "Tài liệu thứ nhất", "hybrid_score": 0.9},
            {"section_id": "second", "content": "Tài liệu thứ hai", "hybrid_score": 0.8},
        ]
        backend = _FixedBackend([-2.0, 4.5])

        result = rerank_candidates("Câu hỏi gốc có $x^2$", candidates, backend)

        self.assertEqual([item["section_id"] for item in result], ["second", "first"])
        self.assertEqual([item["rerank_rank"] for item in result], [1, 2])
        self.assertEqual([item["rerank_score"] for item in result], [4.5, -2.0])
        self.assertNotIn("rerank_score", candidates[0])
        self.assertEqual(
            backend.calls,
            [
                (
                    "Câu hỏi gốc có $x^2$",
                    ["Tài liệu thứ nhất", "Tài liệu thứ hai"],
                )
            ],
        )

    def test_equal_scores_preserve_rrf_order(self) -> None:
        candidates = [
            {"section_id": "first", "content": "Một"},
            {"section_id": "second", "content": "Hai"},
        ]
        result = rerank_candidates("query", candidates, _FixedBackend([1.0, 1.0]))
        self.assertEqual([item["section_id"] for item in result], ["first", "second"])

    def test_invalid_score_count_is_rejected(self) -> None:
        candidates = [{"section_id": "first", "content": "Một"}]
        with self.assertRaisesRegex(ValueError, "1 documents"):
            rerank_candidates("query", candidates, _FixedBackend([]))


if __name__ == "__main__":
    unittest.main()
