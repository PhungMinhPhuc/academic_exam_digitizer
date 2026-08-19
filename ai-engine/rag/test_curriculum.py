"""Focused tests for resolving existing embedding JSON to curriculum.py."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from .curriculum import group_results_by_curriculum, resolve_lesson, select_best_lesson


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class CurriculumResolverTests(unittest.TestCase):
    def test_existing_embedding_records_resolve_to_a_curriculum_lesson(self) -> None:
        source_dir = REPOSITORY_ROOT / "data" / "subject_embed"
        for source_path in source_dir.glob("*.json"):
            payload = json.loads(source_path.read_text(encoding="utf-8"))
            for record in payload["embedding_records"]:
                with self.subTest(record_id=record["id"]):
                    self.assertIsNotNone(resolve_lesson(record["metadata"]))

    def test_results_are_grouped_under_canonical_curriculum_titles(self) -> None:
        result = {
            "section_id": "toan12_ch06_l18_s01",
            "hybrid_score": 1.0,
            "vector_rank": 1,
            "bm25_rank": 2,
            "metadata": {
                "subject": "Toán",
                "grade": 12,
                "chapter_id": "toan12_ch06",
                "lesson_id": "toan12_ch06_l18",
            },
        }

        self.assertEqual(
            group_results_by_curriculum([result]),
            {
                "Toán": {
                    "12": {
                        "Chương 6. Xác suất có điều kiện": {
                            "Bài 18. Xác suất có điều kiện": {
                                "chapter_id": "toan12_ch06",
                                "lesson_id": "toan12_ch06_l18",
                                "sections": [result],
                            }
                        }
                    }
                }
            },
        )

    def test_best_lesson_uses_the_highest_ranked_resolved_section(self) -> None:
        result = {
            "metadata": {
                "subject": "Toán",
                "grade": 12,
                "chapter_id": "toan12_ch01",
                "lesson_id": "toan12_ch01_l01",
            }
        }

        self.assertEqual(
            select_best_lesson([result]),
            {
                "Grade": 12,
                "Chapter": "Chương 1. Ứng dụng đạo hàm để khảo sát và vẽ đồ thị hàm số",
                "Lesson": "Bài 1. Tính đơn điệu và cực trị của hàm số",
                "Complexity": None,
            },
        )

    def test_best_lesson_is_all_null_when_no_section_matches_curriculum(self) -> None:
        self.assertEqual(
            select_best_lesson([]),
            {"Grade": None, "Chapter": None, "Lesson": None, "Complexity": None},
        )


if __name__ == "__main__":
    unittest.main()
