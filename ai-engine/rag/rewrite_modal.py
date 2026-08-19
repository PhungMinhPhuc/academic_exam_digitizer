"""Modal worker that rewrites STEM questions before RAG retrieval.

Deploy from ``ai-engine`` with:

    ..\\.venv\\Scripts\\modal.exe deploy rag\\rewrite_modal.py

The deployed rewrite methods are intentionally not public HTTP endpoints.
``rag.rewrite`` calls the selected worker through the authenticated Modal SDK.
"""

from __future__ import annotations

import json
import re
from time import perf_counter
from typing import Any
from uuid import uuid4

import modal


APP_NAME = "exam-rag-qwen3-rewrite"
CLASS_NAME = "Qwen3Rewriter"
CLASS_NAME_4B = "Qwen3Rewriter4B"
MODEL_NAME = "Qwen/Qwen3-14B-AWQ"
MODEL_NAME_4B = "Qwen/Qwen3-4B"
MODEL_CACHE_PATH = "/models/huggingface"
MAX_INPUT_CHARS = 5_000

FORMULA_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["concepts"],
    "properties": {
        "concepts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["index", "description", "confidence"],
                "properties": {
                    "index": {"type": "integer", "minimum": 1},
                    "description": {"type": "string", "minLength": 1},
                    "confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
            },
        },
    },
}

_SUPERSEDED_SYSTEM_PROMPT = r"""Bạn là bước chuẩn hoá truy vấn cho RAG chương trình phổ thông Việt Nam.

Nhiệm vụ: từ câu hỏi Toán, Vật lí hoặc Hoá học có thể chứa LaTeX, tạo một mô tả tiếng Việt ngắn gọn cho từng biểu thức LaTeX toán học.

Không giải bài. Không suy ra đáp số. Không tạo topic_id, nhãn chương, tên bài, taxonomy, từ khoá tìm kiếm hoặc diễn giải toàn bộ câu hỏi.

Chỉ tạo description cho các biểu thức LaTeX. Không mô tả, viết lại hoặc suy diễn từ phần văn bản thông thường.

Ngữ cảnh tiếng Việt chỉ được dùng để phân biệt đúng khái niệm khoa học phổ quát khi biểu thức có nhiều cách hiểu. Không được đặt ý nghĩa ứng dụng riêng cho biến hoặc biểu thức. Ví dụ, không gọi `y=x` là chi phí, năng lượng hoặc quãng đường nếu đề không khẳng định đó là định nghĩa chuẩn của công thức.

Description phải:
- là một cụm danh từ tiếng Việt ngắn gọn, tối đa 16 từ;
- ưu tiên tên chuẩn của định luật, công thức, định lý hoặc dạng phương trình nếu xác định được;
- nếu chưa đủ xác định, dùng mô tả toán học/vật lí/hoá học trung tính, không đoán tên riêng;
- không chứa LaTeX, không chép lại biểu thức, không chứa lời giải.

Chỉ xét biểu thức nằm trong `$...$`, `$$...$$`, `\(...\)` hoặc `\[...\]`.
Mỗi biểu thức tạo đúng một phần tử trong `concepts`, kể cả biểu thức lặp lại.
Giữ thứ tự tuyệt đối từ trái sang phải.
Nếu không có biểu thức LaTeX, trả về chính xác `{"concepts":[]}`.

Chỉ trả về một JSON object hợp lệ, không Markdown, không có trường nào khác:

{
  "concepts": [
    {
      "description": "khái niệm hoặc mô tả trung tính",
      "confidence": 0.0
    }
  ]
}

`confidence` là mức chắc chắn nội bộ trong khoảng 0.0 đến 1.0:
- 0.9–1.0: nhận diện trực tiếp và gần như duy nhất;
- 0.6–0.8: có diễn giải hợp lý nhưng còn mơ hồ;
- dưới 0.6: chỉ xác định được mô tả trung tính."""

FORMULA_SYSTEM_PROMPT = r"""Bạn là bước chuẩn hoá công thức cho RAG chương trình phổ thông Việt Nam.

Nhiệm vụ: tạo một mô tả tiếng Việt ngắn gọn cho TỪNG công thức trong danh sách
"Công thức bắt buộc" do hệ thống cung cấp. Danh sách này là nguồn duy nhất xác định
số lượng và thứ tự công thức.

Phải trả đúng một phần tử cho mỗi index từ 1 đến N, không thiếu, không thừa, không
gộp công thức, kể cả khi công thức lặp lại hoặc là một đáp án ngắn. Không được bỏ qua
công thức vì cho rằng nó ít quan trọng.

Không giải bài. Không suy ra đáp số. Không tạo topic_id, nhãn chương, tên bài,
taxonomy, từ khoá tìm kiếm hoặc diễn giải toàn bộ câu hỏi.

Ngữ cảnh câu hỏi chỉ được dùng để phân biệt khái niệm Toán, Vật lí hoặc Hoá học phổ
quát khi một công thức có nhiều cách hiểu. Không được suy diễn ý nghĩa ứng dụng riêng
cho biến hoặc biểu thức. Ví dụ, không gọi `y=x` là chi phí, năng lượng hoặc quãng đường.

Mỗi description phải là một cụm danh từ tiếng Việt trung tính, tối đa 16 từ:
- ưu tiên tên chuẩn của định luật, công thức, định lý hoặc dạng phương trình khi xác định được;
- nếu chưa đủ xác định, mô tả trung tính về quan hệ toán học, vật lí hoặc hoá học;
- không chứa LaTeX, không chép lại công thức, không chứa lời giải, đáp số hoặc diễn giải dài.

Chỉ trả về một JSON object hợp lệ, không Markdown, không có trường nào khác:
{
  "concepts": [
    {
      "index": 1,
      "description": "khái niệm hoặc mô tả trung tính",
      "confidence": 0.0
    }
  ]
}

`confidence` là mức chắc chắn nội bộ trong khoảng 0.0 đến 1.0:
- 0.9–1.0: nhận diện trực tiếp và gần như duy nhất;
- 0.6–0.8: có diễn giải hợp lý nhưng còn mơ hồ;
- dưới 0.6: chỉ xác định được mô tả trung tính."""

METHOD_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "relevant_givens",
        "target",
        "transformation",
        "method",
        "query",
        "confidence",
    ],
    "properties": {
        "relevant_givens": {
            "type": "array",
            "minItems": 1,
            "maxItems": 5,
            "items": {"type": "string", "minLength": 1},
        },
        "target": {"type": "string", "minLength": 1},
        "transformation": {"type": "string", "minLength": 1},
        "method": {"type": "string", "minLength": 1},
        "query": {"type": "string", "minLength": 1},
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        },
    },
}

METHOD_SYSTEM_PROMPT = r"""Bạn tạo một truy vấn phương pháp để phân loại câu hỏi
vào đúng phần kiến thức phổ thông Việt Nam.

Đọc toàn bộ câu hỏi và suy ra quan hệ, nguyên lý hoặc phép biến đổi toán học cần
dùng cho phần nhỏ đang được hỏi. Trả thêm dữ kiện liên quan, mục tiêu, hướng biến
đổi và tên phương pháp để hệ thống tự tạo truy vấn rerank. Không tự chọn bài học.

Các trường phải dùng ngôn ngữ kiến thức chuẩn, gần với cách diễn đạt trong sách
giáo khoa và tài liệu phân loại:
- đặt tên kiến thức hoặc phép biến đổi chính ở đầu truy vấn;
- ưu tiên các cụm như tên khái niệm, dạng toán và cách vận dụng kiến thức;
- lược bỏ số liệu, thời điểm, tên vật thể và bối cảnh thực tế không cần thiết cho
  việc xác định phần kiến thức;
- mô tả bài toán thực tế bằng dạng vận dụng tổng quát, không kể lại tình huống.

Được phép:
- gọi tên phép toán, định lý, định luật, mô hình hình học hoặc quan hệ giữa các đại lượng;
- suy ra kiến thức cần dùng dù đề không nêu trực tiếp, ví dụ vận tốc được tìm bằng
  nguyên hàm của gia tốc hoặc kiểm tra điểm thuộc khối cầu bằng khoảng cách tới tâm.

Ví dụ, ưu tiên "tích phân xác định; vận dụng tích phân để tìm vận tốc từ gia tốc"
thay vì "tính vận tốc tên lửa tại thời điểm 30 giây".

Không được:
- thực hiện phép tính, thay số, rút gọn biểu thức hoặc kết luận đáp án đúng/sai;
- trình bày lời giải, các bước giải chi tiết hoặc sinh nhiều truy vấn;
- tạo Grade, Chapter, Lesson, lesson_id, topic_id hay nhãn taxonomy;
- chép lại nguyên câu hỏi hoặc chứa LaTeX.

Giới hạn:
- relevant_givens gồm 1 đến 5 cụm, mỗi cụm tối đa 16 từ;
- target tối đa 20 từ;
- transformation tối đa 30 từ và phải nêu đúng chiều biến đổi;
- method tối đa 16 từ;
- query là một câu truy vấn tổng hợp tối đa 40 từ.

Chỉ trả về một JSON object hợp lệ, không Markdown, không có trường nào khác:
{
  "relevant_givens": [
    "dữ kiện hoặc đại lượng liên quan"
  ],
  "target": "đại lượng hoặc kết luận cần xác định",
  "transformation": "chiều biến đổi từ dữ kiện tới mục tiêu",
  "method": "phương pháp trực tiếp cần dùng",
  "query": "một câu mô tả kiến thức và phép biến đổi cần dùng",
  "confidence": 0.0
}

`confidence` là mức chắc chắn nội bộ trong khoảng 0.0 đến 1.0."""

LATEX_EXPRESSION_RE = re.compile(
    r"\$\$(?P<display_dollar>.+?)\$\$"
    r"|\\\[(?P<display_bracket>.+?)\\\]"
    r"|\\\((?P<inline_bracket>.+?)\\\)"
    r"|(?<!\$)\$(?!\$)(?P<inline_dollar>.+?)(?<!\$)\$(?!\$)",
    re.DOTALL,
)
TAXONOMY_LABEL_RE = re.compile(
    r"\b(?:lesson_id|chapter_id|section_id|topic_id)\b"
    r"|\b(?:Grade|Chapter|Lesson)\s*:"
    r"|\b(?:Chương|Bài)\s+\d+\b",
    re.IGNORECASE,
)

app = modal.App(APP_NAME)
model_cache = modal.Volume.from_name(
    "exam-rag-qwen3-14b-awq-cache", create_if_missing=True
)
model_cache_4b = modal.Volume.from_name(
    "exam-rag-qwen3-4b-cache", create_if_missing=True
)

# Qwen3-14B-AWQ is an official 4-bit Qwen release and runs on stable vLLM.
# Keep inference dependencies isolated in the Modal image.
image = (
    modal.Image.from_registry(
        "nvidia/cuda:13.0.1-devel-ubuntu22.04",
        add_python="3.12",
    )
    .run_commands(
        "python -m pip install --no-cache-dir uv",
        "uv pip install --system --upgrade vllm --torch-backend=cu130",
        "python -c \"import vllm; print(vllm.__version__)\"",
    )
)


def _worker_log(event: str, **fields: Any) -> None:
    """Emit one structured line that Modal collects as container stdout."""
    print(
        json.dumps(
            {"component": "rewrite-worker", "event": event, **fields},
            ensure_ascii=False,
        ),
        flush=True,
    )


def _escape_latex_backslashes_in_json(text: str) -> str:
    r"""Make raw LaTex commands inside model-generated JSON valid JSON strings.

    Models commonly emit ``\frac`` or ``\mid`` in a JSON string with one
    backslash. JSON treats these as invalid (and treats ``\frac`` as ``\f`` +
    ``rac``), although they are valid LaTex. Preserve JSON quote/backslash
    escapes and double every other backslash occurring inside a string.
    """
    repaired: list[str] = []
    in_string = False
    index = 0
    while index < len(text):
        character = text[index]
        if character == '"':
            previous = text[index - 1] if index else ""
            if previous != "\\":
                in_string = not in_string
            repaired.append(character)
        elif character == "\\" and in_string:
            next_character = text[index + 1] if index + 1 < len(text) else ""
            unicode_escape = text[index + 2 : index + 6]
            if next_character in {'"', "\\"} or (
                next_character == "u"
                and len(unicode_escape) == 4
                and all(digit in "0123456789abcdefABCDEF" for digit in unicode_escape)
            ):
                repaired.append(character)
            else:
                repaired.append("\\\\")
        else:
            repaired.append(character)
        index += 1
    return "".join(repaired)


def _extract_json(text: str) -> dict[str, Any]:
    """Return the first JSON object generated by the model, or raise clearly."""
    decoder = json.JSONDecoder()
    start = text.find("{")
    while start >= 0:
        try:
            value, _ = decoder.raw_decode(_escape_latex_backslashes_in_json(text[start:]))
        except json.JSONDecodeError:
            start = text.find("{", start + 1)
            continue
        if isinstance(value, dict):
            return value
        start = text.find("{", start + 1)
    raise ValueError(f"Model did not return a JSON object: {text!r}")


def _formula_matches(question: str) -> list[re.Match[str]]:
    """Extract immutable, ordered formula spans from the original query."""
    return list(LATEX_EXPRESSION_RE.finditer(question))


def _contains_latex(description: str) -> bool:
    """Reject raw math delimiters and common LaTeX command prefixes."""
    if "$" in description:
        return True
    return any(
        character == "\\"
        and position + 1 < len(description)
        and (description[position + 1].isalpha() or description[position + 1] in "()[]")
        for position, character in enumerate(description)
    )


def _build_user_prompt(question: str, formula_matches: list[re.Match[str]]) -> str:
    """Give the model explicit parser-owned targets rather than span discovery."""
    required_formulas = "\n".join(
        f"{index}. {match.group(0)}"
        for index, match in enumerate(formula_matches, start=1)
    )
    return (
        "Câu hỏi gốc (chỉ dùng làm ngữ cảnh):\n"
        f"{question}\n\n"
        f"Công thức bắt buộc ({len(formula_matches)} biểu thức):\n"
        f"{required_formulas}"
    )


def _build_method_user_prompt(question: str) -> str:
    """Supply the untouched question to the isolated method-classification prompt."""
    return f"Câu hỏi cần phân loại:\n{question}"


def _validated_model_concepts(
    concepts_value: Any,
    formula_count: int,
) -> tuple[list[dict[str, Any]], str | None]:
    """Accept only a complete one-to-one response for parser-owned spans."""
    if not isinstance(concepts_value, list):
        return [], "concepts is not an array"
    if len(concepts_value) != formula_count:
        return [], f"expected {formula_count} descriptions, received {len(concepts_value)}"

    concepts_by_index: dict[int, dict[str, Any]] = {}
    for item in concepts_value:
        if not isinstance(item, dict):
            return [], "concept item is not an object"
        index = item.get("index")
        if isinstance(index, bool) or not isinstance(index, int):
            return [], "concept index is not an integer"
        if index < 1 or index > formula_count or index in concepts_by_index:
            return [], "concept indexes are missing, duplicated, or out of range"

        description = str(item.get("description", "")).strip()
        if not description:
            return [], f"description {index} is empty"
        if len(description.split()) > 16:
            return [], f"description {index} exceeds 16 words"
        if _contains_latex(description):
            return [], f"description {index} contains LaTeX"

        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            return [], f"description {index} has invalid confidence"
        concepts_by_index[index] = {
            "description": description,
            "confidence": min(1.0, max(0.0, confidence)),
        }

    expected_indexes = set(range(1, formula_count + 1))
    if set(concepts_by_index) != expected_indexes:
        return [], "concept indexes do not cover every formula"
    return [concepts_by_index[index] for index in range(1, formula_count + 1)], None


def _replace_latex_expressions_in_order(
    question: str,
    formula_matches: list[re.Match[str]],
    model_concepts: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """Replace parser-owned spans after one-to-one validation."""
    parts: list[str] = []
    concepts: list[dict[str, Any]] = []
    search_start = 0

    for match, model_concept in zip(formula_matches, model_concepts, strict=True):
        parts.append(question[search_start : match.start()])
        parts.append(model_concept["description"])
        concepts.append({"latex": match.group(0), **model_concept})
        search_start = match.end()

    parts.append(question[search_start:])
    return "".join(parts), concepts


def _normalise_formula_response(
    question: str,
    raw_text: str,
    model_name: str = MODEL_NAME,
) -> dict[str, Any]:
    formula_matches = _formula_matches(question)
    if not formula_matches:
        return {
            "original_query": question,
            "formula_query": question,
            "formula_concepts": [],
            "formula_used_fallback": False,
            "formula_fallback_reason": None,
            "model": model_name,
        }

    try:
        payload = _extract_json(raw_text)
    except ValueError as error:
        return {
            "original_query": question,
            "formula_query": question,
            "formula_concepts": [],
            "formula_used_fallback": True,
            "formula_fallback_reason": f"invalid model JSON: {error}",
            "model": model_name,
        }
    model_concepts, fallback_reason = _validated_model_concepts(
        payload.get("concepts"),
        len(formula_matches),
    )
    if fallback_reason is not None:
        return {
            "original_query": question,
            "formula_query": question,
            "formula_concepts": [],
            "formula_used_fallback": True,
            "formula_fallback_reason": fallback_reason,
            "model": model_name,
        }

    semantic_rewrite, concepts = _replace_latex_expressions_in_order(
        question,
        formula_matches,
        model_concepts,
    )

    return {
        "original_query": question,
        "formula_query": semantic_rewrite,
        "formula_concepts": concepts,
        "formula_used_fallback": False,
        "formula_fallback_reason": None,
        "model": model_name,
    }


def _method_fallback(reason: str, model_name: str) -> dict[str, Any]:
    return {
        "method_query": None,
        "method_analysis": None,
        "method_confidence": None,
        "method_used_fallback": True,
        "method_fallback_reason": reason,
        "model": model_name,
    }


def _validated_method_text(
    value: Any,
    field: str,
    max_words: int,
) -> tuple[str, str | None]:
    if not isinstance(value, str):
        return "", f"{field} is not a string"
    text = value.strip()
    if not text:
        return "", f"{field} is empty"
    if len(text.split()) > max_words:
        return "", f"{field} exceeds {max_words} words"
    if _contains_latex(text):
        return "", f"{field} contains LaTeX"
    if TAXONOMY_LABEL_RE.search(text):
        return "", f"{field} contains a taxonomy label"
    return text, None


def _normalise_method_response(
    raw_text: str,
    model_name: str = MODEL_NAME,
) -> dict[str, Any]:
    try:
        payload = _extract_json(raw_text)
    except ValueError as error:
        return _method_fallback(f"invalid model JSON: {error}", model_name)

    expected_fields = {
        "relevant_givens",
        "target",
        "transformation",
        "method",
        "query",
        "confidence",
    }
    unexpected_fields = set(payload) - expected_fields
    if unexpected_fields:
        return _method_fallback(
            "method response has unexpected fields: "
            + ", ".join(sorted(unexpected_fields)),
            model_name,
        )

    givens_value = payload.get("relevant_givens")
    if not isinstance(givens_value, list):
        return _method_fallback("relevant_givens is not an array", model_name)
    if not 1 <= len(givens_value) <= 5:
        return _method_fallback(
            "relevant_givens must contain 1 to 5 items",
            model_name,
        )

    relevant_givens: list[str] = []
    for index, given_value in enumerate(givens_value, start=1):
        given, fallback_reason = _validated_method_text(
            given_value,
            f"relevant_givens[{index}]",
            16,
        )
        if fallback_reason is not None:
            return _method_fallback(fallback_reason, model_name)
        relevant_givens.append(given)

    analysis: dict[str, Any] = {"relevant_givens": relevant_givens}
    for field, max_words in (
        ("target", 20),
        ("transformation", 30),
        ("method", 16),
    ):
        text, fallback_reason = _validated_method_text(
            payload.get(field),
            field,
            max_words,
        )
        if fallback_reason is not None:
            return _method_fallback(fallback_reason, model_name)
        analysis[field] = text

    query, fallback_reason = _validated_method_text(
        payload.get("query"),
        "method query",
        40,
    )
    if fallback_reason is not None:
        return _method_fallback(fallback_reason, model_name)

    confidence_value = payload.get("confidence")
    try:
        if isinstance(confidence_value, bool):
            raise TypeError
        confidence = float(confidence_value)
    except (TypeError, ValueError):
        return _method_fallback("method confidence is invalid", model_name)
    if not 0.0 <= confidence <= 1.0:
        return _method_fallback(
            "method confidence is outside [0, 1]",
            model_name,
        )

    return {
        "method_query": query,
        "method_analysis": analysis,
        "method_confidence": confidence,
        "method_used_fallback": False,
        "method_fallback_reason": None,
        "model": model_name,
    }


def _load_worker(worker: Any, model_name: str, quantization: str | None) -> None:
    from vllm import LLM

    started_at = perf_counter()
    _worker_log(
        "model_load_started",
        model=model_name,
        quantization=quantization or "none",
    )
    worker.model_name = model_name
    try:
        worker.llm = LLM(
            model=model_name,
            quantization=quantization,
            dtype="half",
            max_model_len=4096,
            gpu_memory_utilization=0.85,
            download_dir=MODEL_CACHE_PATH,
            enable_prefix_caching=True,
            enforce_eager=True,
            max_num_seqs=8,
            max_num_batched_tokens=4096,
        )
    except Exception as error:
        _worker_log(
            "model_load_failed",
            model=model_name,
            error_type=type(error).__name__,
            error=str(error),
        )
        raise
    worker.tokenizer = worker.llm.get_tokenizer()
    _worker_log(
        "model_load_completed",
        model=model_name,
        seconds=round(perf_counter() - started_at, 3),
    )


def _rewrite_with_worker(
    worker: Any,
    question: str,
    *,
    formula_rewrite: bool = True,
    method_rewrite: bool = False,
) -> dict[str, Any]:
    from vllm import SamplingParams
    from vllm.sampling_params import StructuredOutputsParams

    if not question.strip():
        raise ValueError("question must not be empty")
    if len(question) > MAX_INPUT_CHARS:
        raise ValueError(f"question exceeds {MAX_INPUT_CHARS} characters")
    if not formula_rewrite and not method_rewrite:
        raise ValueError("formula_rewrite and method_rewrite cannot both be disabled")

    request_id = uuid4().hex[:12]
    started_at = perf_counter()
    formula_matches = _formula_matches(question)
    _worker_log(
        "request_started",
        request_id=request_id,
        model=worker.model_name,
        input_chars=len(question),
        formula_count=len(formula_matches),
        formula_rewrite=formula_rewrite,
        method_rewrite=method_rewrite,
    )

    def generate(
        *,
        task: str,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        max_tokens: int,
    ) -> tuple[str, float]:
        prompt = worker.tokenizer.apply_chat_template(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        _worker_log(
            "generation_started",
            request_id=request_id,
            model=worker.model_name,
            task=task,
        )
        generation_started_at = perf_counter()
        try:
            outputs = worker.llm.generate(
                [prompt],
                SamplingParams(
                    temperature=0.0,
                    max_tokens=max_tokens,
                    structured_outputs=StructuredOutputsParams(json=schema),
                ),
                use_tqdm=False,
            )
        except Exception as error:
            _worker_log(
                "generation_failed",
                request_id=request_id,
                model=worker.model_name,
                task=task,
                error_type=type(error).__name__,
                error=str(error),
            )
            raise
        generation_seconds = perf_counter() - generation_started_at
        _worker_log(
            "generation_completed",
            request_id=request_id,
            model=worker.model_name,
            task=task,
            seconds=round(generation_seconds, 3),
        )
        return outputs[0].outputs[0].text, generation_seconds

    formula_seconds = 0.0
    if formula_rewrite:
        if formula_matches:
            formula_text, formula_seconds = generate(
                task="formula",
                system_prompt=FORMULA_SYSTEM_PROMPT,
                user_prompt=_build_user_prompt(question, formula_matches),
                schema=FORMULA_JSON_SCHEMA,
                max_tokens=1024,
            )
            formula_result = _normalise_formula_response(
                question,
                formula_text,
                model_name=worker.model_name,
            )
        else:
            formula_result = _normalise_formula_response(
                question,
                '{"concepts": []}',
                model_name=worker.model_name,
            )
    else:
        formula_result = {
            "original_query": question,
            "formula_query": None,
            "formula_concepts": [],
            "formula_used_fallback": False,
            "formula_fallback_reason": None,
            "model": worker.model_name,
        }

    method_seconds = 0.0
    if method_rewrite:
        method_text, method_seconds = generate(
            task="method",
            system_prompt=METHOD_SYSTEM_PROMPT,
            user_prompt=_build_method_user_prompt(question),
            schema=METHOD_JSON_SCHEMA,
            max_tokens=256,
        )
        method_result = _normalise_method_response(
            method_text,
            model_name=worker.model_name,
        )
    else:
        method_result = {
            "method_query": None,
            "method_analysis": None,
            "method_confidence": None,
            "method_used_fallback": False,
            "method_fallback_reason": None,
            "model": worker.model_name,
        }

    result = {
        **formula_result,
        **{key: value for key, value in method_result.items() if key != "model"},
        "formula_rewrite_enabled": formula_rewrite,
        "method_rewrite_enabled": method_rewrite,
        "rewrite_timings_seconds": {
            "formula": round(formula_seconds, 3),
            "method": round(method_seconds, 3),
        },
    }
    _worker_log(
        "request_completed",
        request_id=request_id,
        model=worker.model_name,
        formula_used_fallback=result["formula_used_fallback"],
        method_used_fallback=result["method_used_fallback"],
        seconds=round(perf_counter() - started_at, 3),
    )
    return result


@app.cls(
    image=image,
    gpu="L4",
    timeout=10 * 60,
    scaledown_window=120,
    volumes={"/models": model_cache},
)
class Qwen3Rewriter:
    """Single-L4 Qwen3-14B-AWQ worker for short rewrite requests."""

    @modal.enter()
    def load_model(self) -> None:
        _load_worker(self, MODEL_NAME, quantization="awq")
        model_cache.commit()

    @modal.method()
    def warmup(self) -> dict[str, str]:
        _worker_log("warmup_completed", model=self.model_name)
        return {"model": self.model_name, "status": "ready"}

    @modal.method()
    def rewrite(
        self,
        question: str,
        formula_rewrite: bool = True,
        method_rewrite: bool = False,
    ) -> dict[str, Any]:
        return _rewrite_with_worker(
            self,
            question,
            formula_rewrite=formula_rewrite,
            method_rewrite=method_rewrite,
        )


@app.cls(
    image=image,
    gpu="L4",
    timeout=10 * 60,
    scaledown_window=120,
    volumes={"/models": model_cache_4b},
)
class Qwen3Rewriter4B:
    """Single-L4 Qwen3-4B worker for lower-latency rewrite requests."""

    @modal.enter()
    def load_model(self) -> None:
        _load_worker(self, MODEL_NAME_4B, quantization=None)
        model_cache_4b.commit()

    @modal.method()
    def warmup(self) -> dict[str, str]:
        _worker_log("warmup_completed", model=self.model_name)
        return {"model": self.model_name, "status": "ready"}

    @modal.method()
    def rewrite(
        self,
        question: str,
        formula_rewrite: bool = True,
        method_rewrite: bool = False,
    ) -> dict[str, Any]:
        return _rewrite_with_worker(
            self,
            question,
            formula_rewrite=formula_rewrite,
            method_rewrite=method_rewrite,
        )
