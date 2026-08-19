"""Tests for exam parsing and reusable batch classification."""

from __future__ import annotations

import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from .batch_search import (
    ParsedQuery,
    classify_queries,
    default_output_path,
    parse_exam_text,
    write_results,
)
from .search import HybridSearcher, rrf_fuse_views


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class ExamParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.math1_path = REPOSITORY_ROOT / "test" / "math1.txt"
        cls.queries = parse_exam_text(cls.math1_path.read_text(encoding="utf-8"))

    def test_math1_expands_to_34_queries_in_source_order(self) -> None:
        self.assertEqual(len(self.queries), 34)
        self.assertEqual(self.queries[0].label, "PHẦN I - Câu 1")
        self.assertEqual(self.queries[12].label, "PHẦN II - Câu 1a")
        self.assertEqual(self.queries[27].label, "PHẦN II - Câu 4d")
        self.assertEqual(self.queries[28].label, "PHẦN III - Câu 1")
        self.assertEqual(self.queries[-1].label, "PHẦN III - Câu 6")

    def test_multiple_parts_repeat_the_stem_and_keep_only_one_part(self) -> None:
        query = self.queries[12].question
        self.assertIn("Cho hàm số", query)
        self.assertIn("a) Giao điểm", query)
        self.assertNotIn("b) Số nghiệm", query)
        self.assertNotIn("c) Số tiệm cận", query)
        self.assertNotIn("d) Giá trị lớn nhất", query)

    def test_choices_and_answer_lines_are_removed_but_body_is_preserved(self) -> None:
        self.assertNotIn("A.${{u}_{5}}", self.queries[0].question)
        self.assertIn("Doanh thu", self.queries[9].question)
        self.assertIn("Số ngày", self.queries[9].question)
        self.assertIn(r"\begin{align}", self.queries[10].question)
        self.assertNotIn("Đáp án: 41", self.queries[31].question)

    def test_uppercase_parenthesized_choices_are_not_treated_as_parts(self) -> None:
        queries = parse_exam_text(
            "PHẦN I. Trắc nghiệm\n"
            "Câu 1. Chọn đáp án đúng\n"
            "A) Một\nB) Hai\nC) Ba\nD) Bốn"
        )
        self.assertEqual(len(queries), 1)
        self.assertEqual(queries[0].question, "Câu 1. Chọn đáp án đúng")

    def test_default_file_output_is_next_to_input(self) -> None:
        self.assertEqual(
            default_output_path(self.math1_path),
            self.math1_path.with_name("result_math1.json"),
        )


class _FakeSearcher:
    def classify(
        self,
        query,
        *,
        debug=False,
        debug_candidate_count=None,
        progress_callback=None,
    ):
        if progress_callback is not None:
            progress_callback("formula_rewrite_started")
            progress_callback("formula_rewrite_completed")
            progress_callback("search_started")
            progress_callback("search_completed")
            progress_callback("rerank_started")
            progress_callback("rerank_completed")
        classification = {
            "Grade": 11,
            "Chapter": "Quan hệ vuông góc trong không gian",
            "Lesson": "Thể tích",
            "Complexity": "must be replaced",
        }
        if not debug:
            return classification
        return {
            "classification": classification,
            "original_query": query,
            "query_views": {"original": query},
            "rerank_model": "qwen3-reranker-4b",
            "candidate_count": debug_candidate_count,
            "candidates": [
                {"rank": rank, "section_id": f"section-{rank}"}
                for rank in range(1, (debug_candidate_count or 0) + 1)
            ],
        }


class _StagedFakeSearcher(_FakeSearcher):
    def __init__(self) -> None:
        self.events: list[object] = []

    def warmup_rewrite_model(self) -> bool:
        self.events.append("warmup-rewrite")
        return True

    def prepare_rewrites(self, queries: list[str]) -> None:
        self.events.append(("rewrite", list(queries)))

    def release_rewrite_model(self) -> bool:
        self.events.append("release-rewrite")
        return True

    def warmup_rerank_model(self) -> bool:
        self.events.append("warmup-rerank")
        return True

    def classify(self, query, **kwargs):
        self.events.append(("classify", query))
        return super().classify(query, **kwargs)


class BatchClassificationTests(unittest.TestCase):
    def test_batch_rewrites_every_query_before_loading_reranker(self) -> None:
        queries = [
            ParsedQuery("Câu 1. Nội dung", "1", "I"),
            ParsedQuery("Câu 2. Nội dung", "2", "I"),
        ]
        searcher = _StagedFakeSearcher()

        classify_queries(queries, searcher, warmup_modal=True)

        self.assertEqual(
            searcher.events,
            [
                "warmup-rewrite",
                ("rewrite", [query.question for query in queries]),
                "release-rewrite",
                "warmup-rerank",
                ("classify", queries[0].question),
                ("classify", queries[1].question),
            ],
        )

    def test_batch_logs_progress_and_writes_minimal_utf8_records(self) -> None:
        queries = [
            ParsedQuery("Câu 1. Nội dung tiếng Việt", "1", "I"),
            ParsedQuery("Câu 2. Nội dung", "2", "I"),
        ]
        logger = logging.getLogger("rag.test_batch_search")
        with self.assertLogs(logger, level="INFO") as captured:
            results = classify_queries(queries, _FakeSearcher(), logger=logger)

        log_text = "\n".join(captured.output)
        self.assertIn("[1/2]", log_text)
        self.assertIn("Đang tạo formula query", log_text)
        self.assertIn("Đang chạy vector search + BM25 + RRF", log_text)
        self.assertIn("Đang rerank candidates", log_text)
        self.assertIn("Đã xử lý thành công 2/2 query", log_text)
        self.assertEqual(
            list(results[0]),
            ["Question", "Grade", "Chapter", "Lesson", "Complexity"],
        )
        self.assertIsNone(results[0]["Complexity"])

        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "result.json"
            write_results(output_path, results)
            raw_output = output_path.read_text(encoding="utf-8")
            self.assertIn("Nội dung tiếng Việt", raw_output)
            self.assertEqual(json.loads(raw_output), results)

    def test_batch_collects_separate_debug_records_with_ten_candidates(self) -> None:
        queries = [ParsedQuery("Câu 1. Nội dung", "1", "I")]
        debug_records = []

        results = classify_queries(
            queries,
            _FakeSearcher(),
            debug_records=debug_records,
            debug_candidate_count=10,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(len(debug_records), 1)
        debug = debug_records[0]
        self.assertEqual(debug["Label"], "PHẦN I - Câu 1")
        self.assertEqual(
            debug["classification"],
            {
                "Grade": 11,
                "Chapter": "Quan hệ vuông góc trong không gian",
                "Lesson": "Thể tích",
                "Complexity": None,
            },
        )
        self.assertEqual(debug["rerank_model"], "qwen3-reranker-4b")
        self.assertEqual(debug["candidate_count"], 10)
        self.assertEqual(len(debug["candidates"]), 10)


class HybridSearcherTests(unittest.TestCase):
    def test_at_least_one_query_view_must_be_enabled(self) -> None:
        with self.assertRaisesRegex(ValueError, "enable original_query"):
            HybridSearcher(
                "postgresql://example",
                original_query=False,
                formula_rewrite=False,
                method_rewrite=False,
            )

    def test_rerank_scope_cannot_exceed_ten_candidates(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not exceed 10"):
            HybridSearcher("postgresql://example", rerank_k=11)

    def test_multi_view_rrf_preserves_per_view_provenance(self) -> None:
        shared = {
            "book_id": "book",
            "section_id": "section-integral",
            "content": "Tích phân gia tốc để tìm vận tốc",
            "metadata": {},
        }
        fused = rrf_fuse_views(
            {
                "original": (
                    [
                        {
                            **shared,
                            "vector_rank": 3,
                            "cosine_similarity": 0.5,
                        }
                    ],
                    [],
                ),
                "method": (
                    [
                        {
                            **shared,
                            "vector_rank": 1,
                            "cosine_similarity": 0.9,
                        }
                    ],
                    [
                        {
                            **shared,
                            "bm25_rank": 1,
                            "bm25_score": 8.0,
                        }
                    ],
                ),
            },
            rrf_k=20,
        )

        self.assertEqual(fused[0]["section_id"], "section-integral")
        self.assertEqual(fused[0]["query_ranks"]["original"]["vector_rank"], 3)
        self.assertEqual(fused[0]["query_ranks"]["method"]["bm25_rank"], 1)

    @patch("rag.search.PgVectorStore")
    @patch("rag.search.Bm25SearchIndex")
    @patch("rag.search.SentenceTransformer")
    def test_resources_are_loaded_once_and_reused_for_multiple_queries(
        self,
        model_class: MagicMock,
        bm25_class: MagicMock,
        store_class: MagicMock,
    ) -> None:
        model = model_class.return_value
        model.encode.return_value = np.zeros((1, 1024), dtype=np.float32)
        store_class.return_value.vector_search.return_value = []
        bm25_class.return_value.search.return_value = []

        searcher = HybridSearcher(
            "postgresql://example",
            original_query=True,
            formula_rewrite=False,
            rerank=False,
            bm25_index=Path("bm25-test"),
        )
        first = searcher.classify("Câu 1. Query thứ nhất")
        second = searcher.classify("Câu 2. Query thứ hai")

        self.assertEqual(first["Complexity"], None)
        self.assertEqual(second["Complexity"], None)
        model_class.assert_called_once()
        bm25_class.assert_called_once()
        store_class.assert_called_once_with("postgresql://example")
        self.assertEqual(model.encode.call_count, 2)

    @patch("rag.search.PgVectorStore")
    @patch("rag.search.Bm25SearchIndex")
    @patch("rag.search.SentenceTransformer")
    def test_debug_returns_requested_flat_candidates_without_changing_top_k(
        self,
        model_class: MagicMock,
        bm25_class: MagicMock,
        store_class: MagicMock,
    ) -> None:
        model_class.return_value.encode.return_value = np.zeros(
            (1, 1024), dtype=np.float32
        )
        store_class.return_value.vector_search.return_value = [
            {
                "book_id": "toan12_kntt",
                "section_id": f"section-{index}",
                "content": f"Nội dung section {index}",
                "metadata": {
                    "subject": "Toán",
                    "grade": 12,
                    "chapter_id": "toan12_ch04",
                    "lesson_id": "toan12_ch04_l11",
                },
                "vector_rank": index,
                "cosine_similarity": 1.0 - index / 100,
            }
            for index in range(1, 13)
        ]
        bm25_class.return_value.search.return_value = []
        searcher = HybridSearcher(
            "postgresql://example",
            top_k=1,
            original_query=True,
            formula_rewrite=False,
            rerank=False,
            bm25_index=Path("bm25-test"),
        )

        debug = searcher.classify(
            "Tính nguyên hàm",
            debug=True,
            debug_candidate_count=10,
        )

        self.assertEqual(debug["classification"]["Lesson"], "Bài 11. Nguyên hàm")
        self.assertEqual(debug["candidate_count"], 10)
        self.assertEqual(len(debug["candidates"]), 10)
        self.assertEqual(debug["candidates"][0]["rank"], 1)
        self.assertEqual(debug["candidates"][-1]["rank"], 10)
        self.assertEqual(debug["candidates"][0]["Lesson"], "Bài 11. Nguyên hàm")
        grouped_sections = debug["results"]["Toán"]["12"][
            "Chương 4. Nguyên hàm và tích phân"
        ]["Bài 11. Nguyên hàm"]["sections"]
        self.assertEqual(len(grouped_sections), 10)

    @patch("rag.search.rewrite_query_views")
    @patch("rag.search.PgVectorStore")
    @patch("rag.search.Bm25SearchIndex")
    @patch("rag.search.SentenceTransformer")
    def test_modal_rewrite_is_called_when_enabled(
        self,
        model_class: MagicMock,
        bm25_class: MagicMock,
        store_class: MagicMock,
        rewrite_mock: MagicMock,
    ) -> None:
        model_class.return_value.encode.return_value = np.zeros(
            (1, 1024), dtype=np.float32
        )
        store_class.return_value.vector_search.return_value = []
        bm25_class.return_value.search.return_value = []
        rewrite_mock.return_value = {
            "formula_query": "khái niệm lượng giác",
            "formula_concepts": [],
            "formula_used_fallback": False,
            "formula_fallback_reason": None,
            "method_query": None,
            "method_confidence": None,
            "method_used_fallback": False,
            "method_fallback_reason": None,
        }

        searcher = HybridSearcher(
            "postgresql://example",
            original_query=False,
            formula_rewrite=True,
            rerank=False,
            formula_rewrite_model="qwen3-4b",
            bm25_index=Path("bm25-test"),
        )
        query = r"Câu 1. Cho $y=\sin x$"
        searcher.classify(query)

        rewrite_mock.assert_called_once_with(
            query,
            formula_rewrite=True,
            method_rewrite=False,
            app_name="exam-rag-qwen3-rewrite",
            class_name=None,
            model="qwen3-4b",
            show_modal_logs=False,
        )
        encoded_query = model_class.return_value.encode.call_args.args[0][0]
        self.assertEqual(encoded_query, "khái niệm lượng giác")

    @patch("rag.search.rewrite_query_views")
    @patch("rag.search.PgVectorStore")
    @patch("rag.search.Bm25SearchIndex")
    @patch("rag.search.SentenceTransformer")
    def test_prepared_rewrite_is_reused_without_a_second_remote_call(
        self,
        model_class: MagicMock,
        bm25_class: MagicMock,
        store_class: MagicMock,
        rewrite_mock: MagicMock,
    ) -> None:
        model_class.return_value.encode.return_value = np.zeros((1, 1024), dtype=np.float32)
        store_class.return_value.vector_search.return_value = []
        bm25_class.return_value.search.return_value = []
        rewrite_mock.return_value = {
            "formula_query": "khái niệm lượng giác",
            "formula_concepts": [],
            "formula_used_fallback": False,
            "formula_fallback_reason": None,
            "method_query": None,
            "method_confidence": None,
            "method_used_fallback": False,
            "method_fallback_reason": None,
        }
        searcher = HybridSearcher(
            "postgresql://example",
            original_query=False,
            formula_rewrite=True,
            rerank=False,
            bm25_index=Path("bm25-test"),
        )
        query = r"Câu 1. Cho $y=\sin x$"

        searcher.prepare_rewrites([query])
        searcher.classify(query)

        rewrite_mock.assert_called_once_with(
            query,
            formula_rewrite=True,
            method_rewrite=False,
            app_name="exam-rag-qwen3-rewrite",
            class_name=None,
            model="qwen3-4b",
            show_modal_logs=False,
        )

    @patch("rag.search.rewrite_query_views")
    @patch("rag.search.PgVectorStore")
    @patch("rag.search.Bm25SearchIndex")
    @patch("rag.search.SentenceTransformer")
    def test_method_only_retrieves_without_original_or_formula_view(
        self,
        model_class: MagicMock,
        bm25_class: MagicMock,
        store_class: MagicMock,
        rewrite_mock: MagicMock,
    ) -> None:
        model_class.return_value.encode.return_value = np.zeros(
            (1, 1024), dtype=np.float32
        )
        store_class.return_value.vector_search.return_value = []
        bm25_class.return_value.search.return_value = []
        rewrite_mock.return_value = {
            "formula_query": None,
            "formula_concepts": [],
            "formula_used_fallback": False,
            "formula_fallback_reason": None,
            "method_query": "tích phân gia tốc để tìm vận tốc",
            "method_confidence": 0.9,
            "method_used_fallback": False,
            "method_fallback_reason": None,
        }

        searcher = HybridSearcher(
            "postgresql://example",
            original_query=False,
            formula_rewrite=False,
            method_rewrite=True,
            rerank=False,
            bm25_index=Path("bm25-test"),
        )
        debug = searcher.classify("Bài toán tên lửa", debug=True)

        encoded_queries = model_class.return_value.encode.call_args.args[0]
        self.assertEqual(encoded_queries, ["tích phân gia tốc để tìm vận tốc"])
        self.assertEqual(debug["query_views"], {"method": encoded_queries[0]})
        self.assertEqual(
            bm25_class.return_value.search.call_args.kwargs["query"],
            encoded_queries[0],
        )
        rewrite_mock.assert_called_once_with(
            "Bài toán tên lửa",
            formula_rewrite=False,
            method_rewrite=True,
            app_name="exam-rag-qwen3-rewrite",
            class_name=None,
            model="qwen3-4b",
            show_modal_logs=False,
        )

    @patch("rag.search.rewrite_query_views")
    @patch("rag.search.PgVectorStore")
    @patch("rag.search.Bm25SearchIndex")
    @patch("rag.search.SentenceTransformer")
    def test_method_only_fails_when_method_generation_falls_back(
        self,
        model_class: MagicMock,
        bm25_class: MagicMock,
        store_class: MagicMock,
        rewrite_mock: MagicMock,
    ) -> None:
        del model_class, bm25_class, store_class
        rewrite_mock.return_value = {
            "formula_query": None,
            "formula_concepts": [],
            "formula_used_fallback": False,
            "formula_fallback_reason": None,
            "method_query": None,
            "method_confidence": None,
            "method_used_fallback": True,
            "method_fallback_reason": "invalid model JSON",
        }
        searcher = HybridSearcher(
            "postgresql://example",
            original_query=False,
            formula_rewrite=False,
            method_rewrite=True,
            rerank=False,
            bm25_index=Path("bm25-test"),
        )

        with self.assertRaisesRegex(RuntimeError, "No usable query view"):
            searcher.classify("Bài toán tên lửa")

    @patch("rag.search.rewrite_query_views")
    @patch("rag.search.PgVectorStore")
    @patch("rag.search.Bm25SearchIndex")
    @patch("rag.search.SentenceTransformer")
    def test_rerank_uses_original_query_before_top_k_is_applied(
        self,
        model_class: MagicMock,
        bm25_class: MagicMock,
        store_class: MagicMock,
        rewrite_mock: MagicMock,
    ) -> None:
        model_class.return_value.encode.return_value = np.zeros(
            (1, 1024), dtype=np.float32
        )
        store_class.return_value.vector_search.return_value = [
            {
                "book_id": "book",
                "section_id": f"section-{index}",
                "content": f"Tài liệu thứ {index}",
                "metadata": {},
                "vector_rank": index,
                "cosine_similarity": 1.0 - index / 100,
            }
            for index in range(1, 13)
        ]
        bm25_class.return_value.search.return_value = []
        rewrite_mock.return_value = {
            "formula_query": "khái niệm hàm số",
            "formula_concepts": [],
            "formula_used_fallback": False,
            "formula_fallback_reason": None,
            "method_query": None,
            "method_confidence": None,
            "method_used_fallback": False,
            "method_fallback_reason": None,
        }
        backend = MagicMock()
        original_query = r"Cho hàm số $y=x^2$"

        with (
            patch("rag.search.rerank_candidates") as rerank_mock,
            patch("rag.search.select_best_lesson") as select_mock,
        ):
            rerank_mock.side_effect = (
                lambda query, candidates, selected_backend: list(reversed(candidates))
            )
            select_mock.return_value = {
                "Grade": None,
                "Chapter": None,
                "Lesson": None,
                "Complexity": None,
            }
            searcher = HybridSearcher(
                "postgresql://example",
                top_k=1,
                original_query=False,
                formula_rewrite=True,
                rerank=True,
                rerank_backend=backend,
                bm25_index=Path("bm25-test"),
            )
            searcher.classify(original_query)

        rerank_query, rerank_input, selected_backend = rerank_mock.call_args.args
        self.assertEqual(rerank_query, original_query)
        self.assertEqual(len(rerank_input), 10)
        self.assertIs(selected_backend, backend)
        selected = select_mock.call_args.args[0]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["section_id"], "section-10")

    @patch("rag.search.rewrite_query_views")
    @patch("rag.search.PgVectorStore")
    @patch("rag.search.Bm25SearchIndex")
    @patch("rag.search.SentenceTransformer")
    def test_structured_mode_reranks_with_focus_and_method_analysis(
        self,
        model_class: MagicMock,
        bm25_class: MagicMock,
        store_class: MagicMock,
        rewrite_mock: MagicMock,
    ) -> None:
        model_class.return_value.encode.return_value = np.zeros(
            (1, 1024), dtype=np.float32
        )
        store_class.return_value.vector_search.return_value = [
            {
                "book_id": "book",
                "section_id": f"section-{index}",
                "content": f"Tài liệu thứ {index}",
                "metadata": {},
                "vector_rank": index,
                "cosine_similarity": 1.0 - index / 100,
            }
            for index in range(1, 13)
        ]
        bm25_class.return_value.search.return_value = []
        rewrite_mock.return_value = {
            "formula_query": None,
            "formula_concepts": [],
            "formula_used_fallback": False,
            "formula_fallback_reason": None,
            "method_query": "tích phân gia tốc để tìm vận tốc",
            "method_analysis": {
                "relevant_givens": [
                    "vận tốc ban đầu",
                    "gia tốc tầng một là hàm theo thời gian",
                ],
                "target": "vận tốc tại thời điểm ba mươi giây",
                "transformation": "từ gia tốc suy ra độ biến thiên vận tốc",
                "method": "tích phân xác định của gia tốc",
            },
            "method_confidence": 0.9,
            "method_used_fallback": False,
            "method_fallback_reason": None,
        }
        backend = MagicMock()
        original_query = (
            "Câu 3. Gia tốc tầng hai không liên quan.\n"
            "a) Vận tốc tại thời điểm 30 giây là 1400 m/s."
        )

        with (
            patch("rag.search.rerank_candidates") as rerank_mock,
            patch("rag.search.select_best_lesson") as select_mock,
        ):
            rerank_mock.side_effect = (
                lambda query, candidates, selected_backend: list(candidates)
            )
            select_mock.return_value = {
                "Grade": None,
                "Chapter": None,
                "Lesson": None,
                "Complexity": None,
            }
            searcher = HybridSearcher(
                "postgresql://example",
                top_k=1,
                original_query=False,
                formula_rewrite=False,
                method_rewrite=True,
                rerank=True,
                rerank_query_mode="structured",
                rerank_backend=backend,
                bm25_index=Path("bm25-test"),
            )
            debug = searcher.classify(original_query, debug=True)

        rerank_query = rerank_mock.call_args.args[0]
        self.assertIn("a) Vận tốc tại thời điểm 30 giây", rerank_query)
        self.assertIn("tích phân xác định của gia tốc", rerank_query)
        self.assertNotIn("Gia tốc tầng hai không liên quan", rerank_query)
        self.assertEqual(debug["rerank_query_mode_effective"], "structured")
        self.assertFalse(debug["rerank_query_used_fallback"])


if __name__ == "__main__":
    unittest.main()
