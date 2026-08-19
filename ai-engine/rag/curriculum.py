"""Resolve RAG section identifiers to the canonical curriculum hierarchy."""

from __future__ import annotations

import importlib.util
import re
import unicodedata
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CURRICULUM_PATH = REPOSITORY_ROOT / "curriculum.py"
CHAPTER_NUMBER_RE = re.compile(r"^Chương\s+(\d+)\.")
LESSON_NUMBER_RE = re.compile(r"^Bài\s+(\d+)\.")
IDENTIFIER_RE = re.compile(r"_ch(\d+)_l(\d+)$")


def normalized_subject(value: str) -> str:
    """Compare subject labels without case or Vietnamese accent differences."""
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def load_curriculum_data() -> dict[str, dict[str, dict[str, list[str]]]]:
    """Load ``DATA`` from the repository-level curriculum source of truth."""
    spec = importlib.util.spec_from_file_location("exam_curriculum", CURRICULUM_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load curriculum data from {CURRICULUM_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = getattr(module, "DATA", None)
    if not isinstance(data, dict):
        raise ValueError(f"{CURRICULUM_PATH} must define DATA as a dictionary")
    return data


@lru_cache(maxsize=1)
def curriculum_index() -> dict[tuple[str, int, int, int], dict[str, str]]:
    """Index curriculum titles by subject, grade, chapter number, and lesson number."""
    index: dict[tuple[str, int, int, int], dict[str, str]] = {}
    for subject, grades in load_curriculum_data().items():
        for grade_text, chapters in grades.items():
            grade = int(grade_text)
            for chapter, lessons in chapters.items():
                chapter_match = CHAPTER_NUMBER_RE.match(chapter)
                if chapter_match is None:
                    # curriculum.py also contains non-Chương branches for
                    # subjects outside the current chNN/lNN embedding schema.
                    continue
                chapter_number = int(chapter_match.group(1))
                for lesson in lessons:
                    lesson_match = LESSON_NUMBER_RE.match(lesson)
                    if lesson_match is None:
                        continue
                    lesson_number = int(lesson_match.group(1))
                    key = (normalized_subject(subject), grade, chapter_number, lesson_number)
                    if key in index:
                        raise ValueError(f"Duplicate curriculum key: {key}")
                    index[key] = {
                        "subject": subject,
                        "chapter": chapter,
                        "lesson": lesson,
                    }
    return index


def resolve_lesson(metadata: dict[str, Any]) -> dict[str, str] | None:
    """Return the canonical chapter/lesson for a section's metadata, if present."""
    subject = metadata.get("subject")
    grade = metadata.get("grade")
    lesson_id = metadata.get("lesson_id")
    if not isinstance(subject, str) or not isinstance(grade, int) or not isinstance(lesson_id, str):
        return None

    identifier_match = IDENTIFIER_RE.search(lesson_id)
    if identifier_match is None:
        return None
    chapter_number, lesson_number = map(int, identifier_match.groups())
    resolved = curriculum_index().get(
        (normalized_subject(subject), grade, chapter_number, lesson_number)
    )
    if resolved is None:
        return None
    return {
        "subject": resolved["subject"],
        "grade": str(grade),
        "chapter": resolved["chapter"],
        "lesson": resolved["lesson"],
        "chapter_id": metadata.get("chapter_id", ""),
        "lesson_id": lesson_id,
    }


def select_best_lesson(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the highest-ranked section as the downstream lesson label."""
    empty_result = {
        "Grade": None,
        "Chapter": None,
        "Lesson": None,
        "Complexity": None,
    }
    for result in results:
        metadata = result.get("metadata")
        if not isinstance(metadata, dict):
            continue
        path = resolve_lesson(metadata)
        if path is None:
            continue
        return {
            "Grade": int(path["grade"]),
            "Chapter": path["chapter"],
            "Lesson": path["lesson"],
            "Complexity": None,
        }
    return empty_result


def group_results_by_curriculum(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Group retrieved sections as subject -> grade -> chapter -> lesson.

    The hierarchy's visible titles always come from ``curriculum.py``; only
    retrieved sections are included, ordered as in the already ranked results.
    """
    grouped: dict[str, Any] = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    for result in results:
        metadata = result.get("metadata")
        if not isinstance(metadata, dict):
            continue
        path = resolve_lesson(metadata)
        if path is None:
            continue

        lessons = grouped[path["subject"]][path["grade"]][path["chapter"]]
        lesson_entry = lessons.setdefault(
            path["lesson"],
            {
                "chapter_id": path["chapter_id"],
                "lesson_id": path["lesson_id"],
                "sections": [],
            },
        )
        lesson_entry["sections"].append(result)

    return {
        subject: {
            grade: {chapter: dict(lessons) for chapter, lessons in chapters.items()}
            for grade, chapters in grades.items()
        }
        for subject, grades in grouped.items()
    }
