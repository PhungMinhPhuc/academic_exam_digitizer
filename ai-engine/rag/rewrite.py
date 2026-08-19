"""Local CLI client for the deployed Modal Qwen3 query-rewrite workers.

Example, from ``ai-engine`` after deploying ``rag/rewrite_modal.py``:

    ..\\.venv\\Scripts\\python.exe -m rag.rewrite
"""

from __future__ import annotations

import argparse
import json


DEFAULT_FORMULA_REWRITE_APP_NAME = "exam-rag-qwen3-rewrite"
DEFAULT_FORMULA_REWRITE_CLASS_NAME = "Qwen3Rewriter4B"
DEFAULT_FORMULA_REWRITE_MODEL = "qwen3-4b"
FORMULA_REWRITE_MODEL_CLASSES = {
    DEFAULT_FORMULA_REWRITE_MODEL: DEFAULT_FORMULA_REWRITE_CLASS_NAME,
}


def formula_rewrite_class_name(model: str) -> str:
    """Resolve a user-facing rewrite model name to its deployed Modal class."""
    try:
        return FORMULA_REWRITE_MODEL_CLASSES[model]
    except KeyError as error:
        choices = ", ".join(FORMULA_REWRITE_MODEL_CLASSES)
        raise ValueError(f"Unknown rewrite model {model!r}; choose one of: {choices}") from error


def read_query_from_terminal() -> str:
    """Read a multi-line question pasted into the terminal.

    A blank line submits the question. This avoids PowerShell interpreting
    LaTex dollar signs when the query is supplied as a command-line argument.
    """
    print("Nhập hoặc dán query. Kết thúc bằng một dòng trống:")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line:
            break
        lines.append(line)

    query = "\n".join(lines).strip()
    if not query:
        raise ValueError("query must not be empty")
    return query


def rewrite_query_views(
    query: str,
    *,
    formula_rewrite: bool,
    method_rewrite: bool,
    app_name: str = DEFAULT_FORMULA_REWRITE_APP_NAME,
    class_name: str | None = None,
    model: str = DEFAULT_FORMULA_REWRITE_MODEL,
    show_modal_logs: bool = False,
) -> dict[str, object]:
    """Call enabled rewrite tasks on the deployed worker."""
    if not formula_rewrite and not method_rewrite:
        raise ValueError("formula_rewrite and method_rewrite cannot both be disabled")
    try:
        import modal
    except ImportError as error:
        raise RuntimeError(
            "Missing dependency 'modal'. Install ai-engine/rag/requirements.txt first."
        ) from error

    selected_class_name = class_name or formula_rewrite_class_name(model)
    rewriter_class = modal.Cls.from_name(app_name, selected_class_name)
    if show_modal_logs:
        with modal.enable_output():
            return rewriter_class().rewrite.remote(
                query,
                formula_rewrite=formula_rewrite,
                method_rewrite=method_rewrite,
            )
    return rewriter_class().rewrite.remote(
        query,
        formula_rewrite=formula_rewrite,
        method_rewrite=method_rewrite,
    )


def spawn_query_rewrite_warmup(
    app_name: str = DEFAULT_FORMULA_REWRITE_APP_NAME,
    class_name: str | None = None,
    model: str = DEFAULT_FORMULA_REWRITE_MODEL,
) -> object:
    """Start a non-blocking Modal call that loads the selected rewrite model."""
    try:
        import modal
    except ImportError as error:
        raise RuntimeError(
            "Missing dependency 'modal'. Install ai-engine/rag/requirements.txt first."
        ) from error

    selected_class_name = class_name or formula_rewrite_class_name(model)
    rewriter_class = modal.Cls.from_name(app_name, selected_class_name)
    return rewriter_class().warmup.spawn()


def release_query_rewrite_worker(
    app_name: str = DEFAULT_FORMULA_REWRITE_APP_NAME,
    class_name: str | None = None,
    model: str = DEFAULT_FORMULA_REWRITE_MODEL,
) -> dict[str, object]:
    """Release the selected worker's rewrite model after a batch phase."""
    try:
        import modal
    except ImportError as error:
        raise RuntimeError(
            "Missing dependency 'modal'. Install ai-engine/rag/requirements.txt first."
        ) from error

    selected_class_name = class_name or formula_rewrite_class_name(model)
    rewriter_class = modal.Cls.from_name(app_name, selected_class_name)
    response = rewriter_class().release.remote()
    if not isinstance(response, dict):
        raise ValueError("Modal rewrite release response must be an object")
    return response


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create formula and/or method query views through Modal Qwen3."
    )
    parser.add_argument("--app-name", default=DEFAULT_FORMULA_REWRITE_APP_NAME)
    parser.add_argument(
        "--formula-rewrite",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--method-rewrite",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument(
        "--formula-rewrite-model",
        choices=FORMULA_REWRITE_MODEL_CLASSES,
        default=DEFAULT_FORMULA_REWRITE_MODEL,
    )
    parser.add_argument(
        "--class-name",
        default=None,
        help="Override the Modal class selected by --formula-rewrite-model",
    )
    parser.add_argument(
        "--modal-logs",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Stream Modal worker output to this terminal (default: enabled)",
    )
    args = parser.parse_args()

    if not args.formula_rewrite and not args.method_rewrite:
        parser.error("enable --formula-rewrite, --method-rewrite, or both")

    try:
        query = read_query_from_terminal()
        result = rewrite_query_views(
            query,
            formula_rewrite=args.formula_rewrite,
            method_rewrite=args.method_rewrite,
            app_name=args.app_name,
            class_name=args.class_name,
            model=args.formula_rewrite_model,
            show_modal_logs=args.modal_logs,
        )
    except (RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
