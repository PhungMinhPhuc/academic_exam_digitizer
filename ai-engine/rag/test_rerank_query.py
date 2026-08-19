"""Tests for parser-owned focus and deterministic structured rerank queries."""

from __future__ import annotations

import unittest

from .rerank_query import (
    build_structured_rerank_query,
    parse_query_context,
    select_rerank_query,
    validate_method_analysis,
)


METHOD_ANALYSIS = {
    "relevant_givens": [
        "vận tốc ban đầu",
        "gia tốc tầng một là hàm theo thời gian",
        "khoảng thời gian từ không đến ba mươi giây",
    ],
    "target": "vận tốc tại thời điểm ba mươi giây",
    "transformation": "từ gia tốc suy ra độ biến thiên vận tốc trên một khoảng",
    "method": "tích phân xác định của gia tốc",
}


class QueryContextTests(unittest.TestCase):
    def test_one_part_keeps_exact_focus_and_separates_stem(self) -> None:
        query = (
            "Câu 3. Tên lửa có gia tốc tầng một và tầng hai.\n"
            "a) Vận tốc tại thời điểm 30 giây là 1400 m/s."
        )

        context = parse_query_context(query)

        self.assertEqual(context.part, "a")
        self.assertEqual(context.stem, "Câu 3. Tên lửa có gia tốc tầng một và tầng hai.")
        self.assertEqual(
            context.focused_subquestion,
            "a) Vận tốc tại thời điểm 30 giây là 1400 m/s.",
        )
        self.assertFalse(context.used_fallback)

    def test_query_without_part_uses_the_complete_original(self) -> None:
        query = "Câu 1. Tính nguyên hàm của hàm số."

        context = parse_query_context(query)

        self.assertIsNone(context.part)
        self.assertEqual(context.focused_subquestion, query)
        self.assertFalse(context.used_fallback)

    def test_multiple_parts_fall_back_to_the_original_query(self) -> None:
        query = "Câu 1. Đề chung.\na) Mệnh đề một.\nb) Mệnh đề hai."

        context = parse_query_context(query)

        self.assertTrue(context.used_fallback)
        self.assertEqual(context.focused_subquestion, query)
        self.assertIn("multiple subquestions", context.fallback_reason)


class StructuredRerankQueryTests(unittest.TestCase):
    def test_builder_uses_focus_and_open_method_fields_without_full_stem(self) -> None:
        context = parse_query_context(
            "Câu 3. Gia tốc tầng hai không liên quan.\n"
            "a) Vận tốc tại thời điểm 30 giây là 1400 m/s."
        )

        query = build_structured_rerank_query(context, METHOD_ANALYSIS)

        self.assertIn("a) Vận tốc tại thời điểm 30 giây", query)
        self.assertIn("tích phân xác định của gia tốc", query)
        self.assertIn("Hướng biến đổi", query)
        self.assertNotIn("Gia tốc tầng hai không liên quan", query)

    def test_method_analysis_rejects_taxonomy_labels_and_latex(self) -> None:
        with_label = {**METHOD_ANALYSIS, "method": "Lesson: Tích phân"}
        with_latex = {**METHOD_ANALYSIS, "target": "tính $v(30)$"}

        _, label_reason = validate_method_analysis(with_label)
        _, latex_reason = validate_method_analysis(with_latex)

        self.assertIn("taxonomy label", label_reason)
        self.assertIn("LaTeX", latex_reason)

    def test_structured_mode_uses_structured_query_when_all_signals_are_valid(self) -> None:
        original = "Câu 3. Đề chung.\na) Kiểm tra vận tốc."
        context = parse_query_context(original)

        selection = select_rerank_query(
            original_query=original,
            context=context,
            requested_mode="structured",
            method_rewrite_enabled=True,
            method_analysis=METHOD_ANALYSIS,
            method_confidence=0.92,
            method_used_fallback=False,
            min_confidence=0.7,
        )

        self.assertEqual(selection.effective_mode, "structured")
        self.assertIn("Phương pháp trực tiếp cần dùng", selection.query)
        self.assertFalse(selection.used_fallback)

    def test_low_confidence_structured_mode_falls_back_to_original(self) -> None:
        original = "Câu 3. Đề chung.\na) Kiểm tra vận tốc."

        selection = select_rerank_query(
            original_query=original,
            context=parse_query_context(original),
            requested_mode="structured",
            method_rewrite_enabled=True,
            method_analysis=METHOD_ANALYSIS,
            method_confidence=0.4,
            method_used_fallback=False,
            min_confidence=0.7,
        )

        self.assertEqual(selection.effective_mode, "original")
        self.assertEqual(selection.query, original)
        self.assertTrue(selection.used_fallback)
        self.assertIn("below", selection.fallback_reason)

    def test_original_mode_does_not_require_method_analysis(self) -> None:
        original = "Câu hỏi gốc"

        selection = select_rerank_query(
            original_query=original,
            context=parse_query_context(original),
            requested_mode="original",
            method_rewrite_enabled=False,
            method_analysis=None,
            method_confidence=None,
            method_used_fallback=False,
            min_confidence=0.7,
        )

        self.assertEqual(selection.query, original)
        self.assertFalse(selection.used_fallback)


if __name__ == "__main__":
    unittest.main()
