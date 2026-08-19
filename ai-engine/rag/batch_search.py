"""Parse an exam into individual queries and classify them in one RAG run."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Pattern, Protocol

from .build_bm25s import DEFAULT_OUTPUT_DIR
from .rerank import (
    DEFAULT_RERANK_APP_NAME,
    DEFAULT_RERANK_MODEL,
    RERANK_MODEL_CLASSES,
)
from .rerank_query import (
    DEFAULT_RERANK_METHOD_MIN_CONFIDENCE,
    DEFAULT_RERANK_QUERY_MODE,
    PART_PATTERN,
    RERANK_QUERY_MODES,
)
from .rewrite import (
    DEFAULT_FORMULA_REWRITE_APP_NAME,
    DEFAULT_FORMULA_REWRITE_MODEL,
    FORMULA_REWRITE_MODEL_CLASSES,
)
from .search import (
    DEFAULT_CANDIDATE_K,
    DEFAULT_MODEL,
    DEFAULT_RERANK_K,
    DEFAULT_RRF_K,
    HybridSearcher,
    MAX_RERANK_K,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KEYBOARD_OUTPUT = REPOSITORY_ROOT / "test" / "result_keyboard.json"
LOGGER = logging.getLogger("rag.batch_search")


@dataclass(frozen=True)
class ExamParserConfig:
    """Regex profile for exam formats similar to ``test/math1.txt``."""

    section_pattern: Pattern[str] = re.compile(
        r"^\s*PHẦN\s+(?P<section>[IVXLCDM]+)\s*\.", re.IGNORECASE
    )
    question_pattern: Pattern[str] = re.compile(
        r"^\s*Câu\s+(?P<number>\d+)\s*\.", re.IGNORECASE
    )
    part_pattern: Pattern[str] = PART_PATTERN
    option_line_pattern: Pattern[str] = re.compile(r"^\s*A\s*[.)]")
    inline_option_pattern: Pattern[str] = re.compile(
        r"(?:\t+| {2,})A\s*[.)]"
    )
    answer_pattern: Pattern[str] = re.compile(r"^\s*Đáp\s+án\s*:", re.IGNORECASE)
    footer_pattern: Pattern[str] = re.compile(r"^\s*-+\s*HẾT\s*-+\s*$", re.IGNORECASE)


DEFAULT_PARSER_CONFIG = ExamParserConfig()


@dataclass(frozen=True)
class ParsedQuery:
    question: str
    number: str
    section: str | None = None
    part: str | None = None

    @property
    def label(self) -> str:
        question_label = f"Câu {self.number}{self.part or ''}"
        if self.section is None:
            return question_label
        return f"PHẦN {self.section} - {question_label}"


class QueryClassifier(Protocol):
    def classify(
        self,
        query: str,
        *,
        debug: bool = False,
        debug_candidate_count: int | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> dict[str, Any]: ...


ComplexityEstimator = Callable[[str], Any]


def default_complexity_estimator(query: str) -> None:
    """Placeholder for a future complexity model."""
    del query
    return None


def _trim_blank_lines(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def _clean_question_lines(
    lines: list[str],
    config: ExamParserConfig,
    *,
    strip_options: bool,
) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        if config.answer_pattern.match(line) or config.footer_pattern.match(line):
            continue
        if strip_options and config.option_line_pattern.match(line):
            break
        if strip_options:
            inline_option = config.inline_option_pattern.search(line)
            if inline_option is not None:
                line = line[: inline_option.start()].rstrip()
                if line:
                    cleaned.append(line)
                break
        cleaned.append(line.rstrip())
    return _trim_blank_lines(cleaned)


def _expand_question_block(
    lines: list[str],
    number: str,
    section: str | None,
    config: ExamParserConfig,
) -> list[ParsedQuery]:
    part_starts = [
        (index, match.group("part").lower())
        for index, line in enumerate(lines)
        if (match := config.part_pattern.match(line)) is not None
    ]
    if not part_starts:
        question_lines = _clean_question_lines(lines, config, strip_options=True)
        if not question_lines:
            return []
        return [
            ParsedQuery(
                question="\n".join(question_lines),
                number=number,
                section=section,
            )
        ]

    stem_lines = _clean_question_lines(
        lines[: part_starts[0][0]], config, strip_options=False
    )
    if not stem_lines:
        raise ValueError(f"Câu {number} có phần nhỏ nhưng không có đề bài chung")

    queries: list[ParsedQuery] = []
    for position, (start, part) in enumerate(part_starts):
        end = part_starts[position + 1][0] if position + 1 < len(part_starts) else len(lines)
        part_lines = _clean_question_lines(lines[start:end], config, strip_options=True)
        if not part_lines:
            raise ValueError(f"Câu {number}{part}) không có nội dung")
        queries.append(
            ParsedQuery(
                question="\n".join([*stem_lines, *part_lines]),
                number=number,
                section=section,
                part=part,
            )
        )
    return queries


def parse_exam_text(
    text: str,
    config: ExamParserConfig = DEFAULT_PARSER_CONFIG,
) -> list[ParsedQuery]:
    """Split exam text into standalone classification queries."""
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
    queries: list[ParsedQuery] = []
    current_lines: list[str] = []
    current_number: str | None = None
    current_section: str | None = None
    block_section: str | None = None

    def flush_current() -> None:
        nonlocal current_lines, current_number, block_section
        if current_number is not None:
            queries.extend(
                _expand_question_block(
                    current_lines,
                    current_number,
                    block_section,
                    config,
                )
            )
        current_lines = []
        current_number = None
        block_section = None

    for line in normalized_text.split("\n"):
        section_match = config.section_pattern.match(line)
        if section_match is not None:
            flush_current()
            current_section = section_match.group("section").upper()
            continue

        if config.footer_pattern.match(line):
            flush_current()
            continue

        question_match = config.question_pattern.match(line)
        if question_match is not None:
            flush_current()
            current_number = question_match.group("number")
            block_section = current_section
            current_lines = [line.rstrip()]
            continue

        if current_number is not None:
            current_lines.append(line.rstrip())

    flush_current()
    if not queries:
        raise ValueError("Không tìm thấy câu hỏi theo mẫu 'Câu <số>.'")
    return queries


def read_exam_from_terminal(end_marker: str = "END") -> str:
    print(f"Nhập hoặc dán đề. Kết thúc bằng một dòng chỉ chứa {end_marker}:")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == end_marker:
            break
        lines.append(line)
    text = "\n".join(lines)
    if not text.strip():
        raise ValueError("Nội dung đề không được để trống")
    return text


def default_output_path(input_path: Path | None) -> Path:
    if input_path is None:
        return DEFAULT_KEYBOARD_OUTPUT
    return input_path.with_name(f"result_{input_path.stem}.json")


def _preview(text: str, limit: int = 120) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def classify_queries(
    queries: list[ParsedQuery],
    searcher: QueryClassifier,
    *,
    complexity_estimator: ComplexityEstimator = default_complexity_estimator,
    debug_records: list[dict[str, Any]] | None = None,
    debug_candidate_count: int = 10,
    logger: logging.Logger = LOGGER,
) -> list[dict[str, Any]]:
    """Classify all parsed queries and return the minimal output records."""
    results: list[dict[str, Any]] = []
    total = len(queries)
    batch_started_at = perf_counter()

    for index, parsed in enumerate(queries, start=1):
        prefix = f"[{index}/{total}] {parsed.label}"
        query_started_at = perf_counter()
        logger.info("%s | Bắt đầu | %s", prefix, _preview(parsed.question))

        def report_stage(stage: str) -> None:
            stage_messages = {
                "formula_rewrite_started": "Đang tạo formula query",
                "formula_rewrite_completed": "Formula rewrite hoàn tất",
                "method_rewrite_started": "Đang tạo method query",
                "method_rewrite_completed": "Method rewrite hoàn tất",
                "search_started": "Đang chạy vector search + BM25 + RRF",
                "search_completed": "Search hoàn tất",
                "rerank_started": "Đang rerank candidates",
                "rerank_completed": "Rerank hoàn tất",
            }
            message = stage_messages.get(stage)
            if message is not None:
                logger.info("%s | %s", prefix, message)

        try:
            if debug_records is None:
                classification = searcher.classify(
                    parsed.question,
                    progress_callback=report_stage,
                )
                debug_payload = None
            else:
                debug_payload = searcher.classify(
                    parsed.question,
                    debug=True,
                    debug_candidate_count=debug_candidate_count,
                    progress_callback=report_stage,
                )
                classification = debug_payload.get("classification")
                if not isinstance(classification, dict):
                    raise ValueError("Debug response is missing classification")
            complexity = complexity_estimator(parsed.question)
        except Exception as error:
            logger.error("%s | Lỗi | %s", prefix, error)
            raise RuntimeError(f"Không thể xử lý {prefix}: {error}") from error

        record = {
            "Question": parsed.question,
            "Grade": classification.get("Grade"),
            "Chapter": classification.get("Chapter"),
            "Lesson": classification.get("Lesson"),
            "Complexity": complexity,
        }
        results.append(record)
        if debug_payload is not None:
            debug_classification = dict(classification)
            debug_classification["Complexity"] = complexity
            debug_records.append(
                {
                    "Label": parsed.label,
                    "Question": parsed.question,
                    **debug_payload,
                    "classification": debug_classification,
                }
            )
        logger.info(
            "%s | Kết quả: Grade=%s, Chapter=%s, Lesson=%s | %.2fs",
            prefix,
            record["Grade"],
            record["Chapter"],
            record["Lesson"],
            perf_counter() - query_started_at,
        )

    logger.info(
        "Đã xử lý thành công %d/%d query trong %.2fs",
        len(results),
        total,
        perf_counter() - batch_started_at,
    )
    return results


def write_results(output_path: Path, results: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(results, ensure_ascii=False, indent=2) + "\n"
    output_path.write_text(payload, encoding="utf-8")


def configure_console_logging() -> None:
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    if LOGGER.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    LOGGER.addHandler(handler)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tách đề thành từng query và phân loại bằng hybrid RAG."
    )
    parser.add_argument("--input", type=Path, help="File đề UTF-8; bỏ qua để nhập bàn phím")
    parser.add_argument("--output", type=Path, help="File JSON kết quả")
    parser.add_argument(
        "--debug-output",
        type=Path,
        help="File JSON debug riêng chứa candidates của từng query",
    )
    parser.add_argument(
        "--debug-candidates",
        type=int,
        default=10,
        help="Số candidates lưu cho mỗi query; mặc định: 10",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Final ranked results")
    parser.add_argument("--candidate-k", type=int, default=DEFAULT_CANDIDATE_K)
    parser.add_argument("--rrf-k", type=int, default=DEFAULT_RRF_K)
    parser.add_argument(
        "--original-query",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Truy hồi bằng query gốc (mặc định: bật)",
    )
    parser.add_argument(
        "--formula-rewrite",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Truy hồi bằng formula query (mặc định: bật)",
    )
    parser.add_argument(
        "--method-rewrite",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Truy hồi bằng một method query (mặc định: tắt)",
    )
    parser.add_argument(
        "--formula-rewrite-app-name",
        default=DEFAULT_FORMULA_REWRITE_APP_NAME,
    )
    parser.add_argument(
        "--formula-rewrite-model",
        choices=FORMULA_REWRITE_MODEL_CLASSES,
        default=DEFAULT_FORMULA_REWRITE_MODEL,
        help="Model formula/method rewrite trên Modal; mặc định: qwen3-14b-awq",
    )
    parser.add_argument(
        "--formula-rewrite-class-name",
        default=None,
        help="Ghi đè Modal class được chọn bởi --formula-rewrite-model",
    )
    parser.add_argument(
        "--formula-rewrite-modal-logs",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Hiện log formula/method worker trên terminal (mặc định: bật)",
    )
    parser.add_argument(
        "--rerank",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Rerank candidates qua Modal (mặc định: bật)",
    )
    parser.add_argument("--rerank-k", type=int, default=DEFAULT_RERANK_K)
    parser.add_argument(
        "--rerank-query-mode",
        choices=RERANK_QUERY_MODES,
        default=DEFAULT_RERANK_QUERY_MODE,
        help="Query dùng để rerank; mặc định: original",
    )
    parser.add_argument(
        "--rerank-method-min-confidence",
        type=float,
        default=DEFAULT_RERANK_METHOD_MIN_CONFIDENCE,
        help="Structured mode fallback dưới confidence này; mặc định: 0.7",
    )
    parser.add_argument("--rerank-app-name", default=DEFAULT_RERANK_APP_NAME)
    parser.add_argument(
        "--rerank-model",
        choices=RERANK_MODEL_CLASSES,
        default=DEFAULT_RERANK_MODEL,
        help=f"Model rerank trên Modal; mặc định: {DEFAULT_RERANK_MODEL}",
    )
    parser.add_argument(
        "--rerank-class-name",
        default=None,
        help="Ghi đè Modal class được chọn bởi --rerank-model",
    )
    parser.add_argument(
        "--rerank-modal-logs",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Hiện log Modal rerank worker trên terminal (mặc định: bật)",
    )
    parser.add_argument(
        "--modal-warmup",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Khởi động đồng thời rewrite và rerank model (mặc định: bật)",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--device", default=None, help="cpu, cuda, hoặc bỏ qua để tự chọn")
    parser.add_argument("--subject")
    parser.add_argument("--grade", type=int)
    parser.add_argument("--book-id")
    parser.add_argument(
        "--bm25-index",
        type=Path,
        default=Path(os.getenv("RAG_BM25_INDEX_DIR", DEFAULT_OUTPUT_DIR)),
    )
    parser.add_argument(
        "--dsn",
        default=os.getenv("RAG_DATABASE_URL"),
        help="PostgreSQL DSN; mặc định lấy từ RAG_DATABASE_URL",
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
        or args.debug_candidates <= 0
    ):
        parser.error(
            "--top-k, --candidate-k, --rrf-k, --rerank-k, and "
            "--debug-candidates must be positive"
        )
    if args.rerank_k > MAX_RERANK_K:
        parser.error(f"--rerank-k must not exceed {MAX_RERANK_K}")
    if not 0.0 <= args.rerank_method_min_confidence <= 1.0:
        parser.error("--rerank-method-min-confidence must be within [0, 1]")

    configure_console_logging()
    try:
        if args.input is None:
            exam_text = read_exam_from_terminal()
            input_description = "bàn phím"
            input_path = None
        else:
            input_path = args.input.resolve()
            exam_text = input_path.read_text(encoding="utf-8-sig")
            input_description = str(input_path)
        queries = parse_exam_text(exam_text)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    output_path = (args.output or default_output_path(input_path)).resolve()
    debug_output_path = args.debug_output.resolve() if args.debug_output else None
    if debug_output_path == output_path:
        parser.error("--debug-output must be different from --output")
    LOGGER.info("Đầu vào: %s", input_description)
    LOGGER.info("Đã tách %d query", len(queries))
    LOGGER.info("Đầu ra: %s", output_path)
    if debug_output_path is not None:
        LOGGER.info(
            "Debug: %s (%d candidates/query)",
            debug_output_path,
            args.debug_candidates,
        )

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
            logger=LOGGER,
        )
        if (
            args.modal_warmup
            and (args.formula_rewrite or args.method_rewrite)
            and args.rerank
        ):
            searcher.warmup_modal_models_concurrently()
        debug_records: list[dict[str, Any]] | None = (
            [] if debug_output_path is not None else None
        )
        results = classify_queries(
            queries,
            searcher,
            debug_records=debug_records,
            debug_candidate_count=args.debug_candidates,
            logger=LOGGER,
        )
        write_results(output_path, results)
        if debug_output_path is not None and debug_records is not None:
            write_results(debug_output_path, debug_records)
    except Exception as error:
        LOGGER.error("Batch dừng, chưa ghi file kết quả: %s", error)
        raise SystemExit(1) from error

    LOGGER.info("Đã ghi %d kết quả vào %s", len(results), output_path)
    if debug_output_path is not None:
        LOGGER.info("Đã ghi debug vào %s", debug_output_path)


if __name__ == "__main__":
    main()
