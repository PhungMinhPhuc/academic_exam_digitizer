"""Focused contract tests for parser-owned LaTeX replacement."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from .rewrite import (
    DEFAULT_FORMULA_REWRITE_CLASS_NAME,
    DEFAULT_FORMULA_REWRITE_MODEL,
    formula_rewrite_class_name,
    rewrite_query_views,
    spawn_query_rewrite_warmup,
)


class _FakeImage:
    @classmethod
    def from_registry(cls, *args: object, **kwargs: object) -> "_FakeImage":
        return cls()

    def run_commands(self, *args: object, **kwargs: object) -> "_FakeImage":
        return self


class _FakeVolume:
    @classmethod
    def from_name(cls, *args: object, **kwargs: object) -> "_FakeVolume":
        return cls()

    def commit(self) -> None:
        return None


class _FakeApp:
    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def cls(self, *args: object, **kwargs: object):
        return lambda decorated: decorated


def _load_module() -> types.ModuleType:
    sys.modules["modal"] = types.SimpleNamespace(
        App=_FakeApp,
        Image=_FakeImage,
        Volume=_FakeVolume,
        enter=lambda: lambda decorated: decorated,
        method=lambda: lambda decorated: decorated,
    )
    module_path = Path(__file__).with_name("rewrite_modal.py")
    spec = importlib.util.spec_from_file_location("rewrite_modal_under_test", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rewrite_modal = _load_module()


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


class RewriteModalContractTest(unittest.TestCase):
    def test_client_can_spawn_non_blocking_rewrite_warmup(self) -> None:
        expected_call = object()

        class _WarmupMethod:
            def spawn(self):
                return expected_call

        class _RemoteWorker:
            warmup = _WarmupMethod()

        class _RemoteClass:
            @classmethod
            def from_name(cls, app_name: str, class_name: str):
                self.assertEqual(app_name, "exam-rag-qwen3-rewrite")
                self.assertEqual(class_name, "Qwen3Rewriter4B")
                return _RemoteWorker

        fake_modal = types.SimpleNamespace(Cls=_RemoteClass)
        with patch.dict(sys.modules, {"modal": fake_modal}):
            call = spawn_query_rewrite_warmup(model="qwen3-4b")

        self.assertIs(call, expected_call)

    def test_client_streams_modal_output_when_requested(self) -> None:
        events: list[object] = []

        class _RemoteMethod:
            def remote(self, query: str, **kwargs: object) -> dict[str, object]:
                events.append(("remote", query, kwargs))
                return {"formula_query": query}

        class _RemoteWorker:
            rewrite = _RemoteMethod()

        class _RemoteClass:
            @classmethod
            def from_name(cls, app_name: str, class_name: str):
                events.append(("class", app_name, class_name))
                return _RemoteWorker

        @contextmanager
        def enable_output():
            events.append("output_started")
            try:
                yield
            finally:
                events.append("output_stopped")

        fake_modal = types.SimpleNamespace(Cls=_RemoteClass, enable_output=enable_output)
        with patch.dict(sys.modules, {"modal": fake_modal}):
            result = rewrite_query_views(
                "Câu hỏi",
                formula_rewrite=True,
                method_rewrite=False,
                model="qwen3-4b",
                show_modal_logs=True,
            )

        self.assertEqual(result["formula_query"], "Câu hỏi")
        self.assertEqual(
            events,
            [
                ("class", "exam-rag-qwen3-rewrite", "Qwen3Rewriter4B"),
                "output_started",
                (
                    "remote",
                    "Câu hỏi",
                    {"formula_rewrite": True, "method_rewrite": False},
                ),
                "output_stopped",
            ],
        )

    def test_formula_rewrite_model_names_resolve_to_modal_classes(self) -> None:
        self.assertEqual(
            formula_rewrite_class_name(DEFAULT_FORMULA_REWRITE_MODEL),
            DEFAULT_FORMULA_REWRITE_CLASS_NAME,
        )
        self.assertEqual(
            formula_rewrite_class_name("qwen3-4b"), "Qwen3Rewriter4B"
        )

    def test_response_reports_the_selected_model(self) -> None:
        result = rewrite_modal._normalise_formula_response(
            "Câu hỏi không có công thức",
            '{"concepts": []}',
            model_name=rewrite_modal.MODEL_NAME_4B,
        )

        self.assertEqual(result["model"], "Qwen/Qwen3-4B")

    def test_replaces_all_formulas_by_index_not_model_order(self) -> None:
        question = "Giải $x^2=1$ rồi xét \\(F=ma\\)."
        raw_text = _json(
            {
                "concepts": [
                    {"index": 2, "description": "định luật II Newton", "confidence": 0.9},
                    {"index": 1, "description": "phương trình bậc hai", "confidence": 0.8},
                ]
            }
        )

        result = rewrite_modal._normalise_formula_response(question, raw_text)

        self.assertFalse(result["formula_used_fallback"])
        self.assertEqual(
            result["formula_query"],
            "Giải phương trình bậc hai rồi xét định luật II Newton.",
        )
        self.assertEqual(len(result["formula_concepts"]), 2)

    def test_missing_description_preserves_entire_query(self) -> None:
        question = "Giải $x=1$ và $y=2$."
        raw_text = _json(
            {
                "concepts": [
                    {"index": 1, "description": "đẳng thức một ẩn", "confidence": 0.8}
                ]
            }
        )

        result = rewrite_modal._normalise_formula_response(question, raw_text)

        self.assertTrue(result["formula_used_fallback"])
        self.assertEqual(result["formula_query"], question)
        self.assertEqual(result["formula_concepts"], [])

    def test_duplicate_index_preserves_entire_query(self) -> None:
        question = "Giải $x=1$ và $y=2$."
        raw_text = json.dumps(
            {
                "concepts": [
                    {"index": 1, "description": "đẳng thức một ẩn", "confidence": 0.8},
                    {"index": 1, "description": "đẳng thức một ẩn", "confidence": 0.8},
                ]
            }
        )

        result = rewrite_modal._normalise_formula_response(question, raw_text)

        self.assertTrue(result["formula_used_fallback"])
        self.assertIn("duplicated", result["formula_fallback_reason"])

    def test_latex_in_description_preserves_entire_query(self) -> None:
        question = "Giải $x=1$."
        raw_text = _json(
            {
                "concepts": [
                    {"index": 1, "description": "phương trình $x=1$", "confidence": 0.8}
                ]
            }
        )

        result = rewrite_modal._normalise_formula_response(question, raw_text)

        self.assertTrue(result["formula_used_fallback"])
        self.assertIn("contains LaTeX", result["formula_fallback_reason"])

    def test_invalid_json_preserves_entire_query(self) -> None:
        question = "Giải $x=1$."

        result = rewrite_modal._normalise_formula_response(question, "not json")

        self.assertTrue(result["formula_used_fallback"])
        self.assertEqual(result["formula_query"], question)
        self.assertIn("invalid model JSON", result["formula_fallback_reason"])

    def test_method_response_returns_one_short_query(self) -> None:
        result = rewrite_modal._normalise_method_response(
            _json(
                {
                    "query": "tích phân gia tốc để tìm vận tốc từ điều kiện ban đầu",
                    "confidence": 0.92,
                }
            )
        )

        self.assertEqual(
            result["method_query"],
            "tích phân gia tốc để tìm vận tốc từ điều kiện ban đầu",
        )
        self.assertEqual(result["method_confidence"], 0.92)
        self.assertFalse(result["method_used_fallback"])

    def test_invalid_method_response_falls_back_independently(self) -> None:
        result = rewrite_modal._normalise_method_response(
            _json({"query": "tính $v(30)$", "confidence": 0.8})
        )

        self.assertIsNone(result["method_query"])
        self.assertTrue(result["method_used_fallback"])
        self.assertIn("contains LaTeX", result["method_fallback_reason"])


if __name__ == "__main__":
    unittest.main()
