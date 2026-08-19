"""Modal worker for replaceable cross-encoder reranking models.

Deploy from ``ai-engine`` with:

    ..\\.venv\\Scripts\\modal.exe deploy rag\\rerank_modal.py

The worker is called through the authenticated Modal SDK by ``rag.rerank``.
"""

from __future__ import annotations

import json
import gc
from time import perf_counter
from typing import Any
from uuid import uuid4

import modal


APP_NAME = "exam-rag-qwen3-rerank"
MODEL_NAME_06B = "Qwen/Qwen3-Reranker-0.6B"
MODEL_NAME_4B = "Qwen/Qwen3-Reranker-4B"
MODEL_CACHE_PATH = "/models/huggingface"
MAX_QUERY_CHARS = 5_000
MAX_DOCUMENT_CHARS = 10_000
MAX_DOCUMENTS = 100
MAX_SEQUENCE_LENGTH = 4_096
BATCH_SIZE_06B = 16
BATCH_SIZE_4B = 4
RERANK_INSTRUCTION = (
    "Given a Vietnamese high-school exam subquestion or its structured analysis, "
    "rank candidate curriculum sections by whether they provide the direct knowledge "
    "or operation required to solve it. Prefer the required direction of transformation "
    "and solution method over passages that merely mention the same quantities, "
    "formulas, or real-world context. Score only the supplied candidate document."
)

app = modal.App(APP_NAME)
model_cache = modal.Volume.from_name(
    "exam-rag-qwen3-reranker-cache",
    create_if_missing=True,
)
image = (
    modal.Image.from_registry(
        "nvidia/cuda:13.0.1-devel-ubuntu22.04",
        add_python="3.12",
    )
    .run_commands(
        "python -m pip install --no-cache-dir uv",
        "uv pip install --system 'sentence-transformers==5.7.0' --torch-backend=cu130",
        "python -c \"import sentence_transformers, torch; "
        "print(sentence_transformers.__version__, torch.__version__)\"",
    )
)


def _worker_log(event: str, **fields: Any) -> None:
    print(
        json.dumps(
            {"component": "rerank-worker", "event": event, **fields},
            ensure_ascii=False,
        ),
        flush=True,
    )


def _validate_request(query: str, documents: list[str]) -> None:
    if not query.strip():
        raise ValueError("query must not be empty")
    if len(query) > MAX_QUERY_CHARS:
        raise ValueError(f"query exceeds {MAX_QUERY_CHARS} characters")
    if not documents:
        raise ValueError("documents must not be empty")
    if len(documents) > MAX_DOCUMENTS:
        raise ValueError(f"documents exceeds {MAX_DOCUMENTS} items")
    for index, document in enumerate(documents):
        if not isinstance(document, str) or not document.strip():
            raise ValueError(f"document {index} must be a non-empty string")
        if len(document) > MAX_DOCUMENT_CHARS:
            raise ValueError(
                f"document {index} exceeds {MAX_DOCUMENT_CHARS} characters"
            )


def _load_worker(worker: Any, model_name: str, batch_size: int) -> None:
    import torch
    from sentence_transformers import CrossEncoder

    started_at = perf_counter()
    _worker_log("model_load_started", model=model_name)
    worker.model_name = model_name
    worker.batch_size = batch_size
    try:
        worker.model = CrossEncoder(
            model_name,
            device="cuda",
            cache_folder=MODEL_CACHE_PATH,
            max_length=MAX_SEQUENCE_LENGTH,
            prompts={"curriculum": RERANK_INSTRUCTION},
            default_prompt_name="curriculum",
            model_kwargs={"torch_dtype": torch.float16},
        )
    except Exception as error:
        _worker_log(
            "model_load_failed",
            model=model_name,
            error_type=type(error).__name__,
            error=str(error),
        )
        raise
    _worker_log(
        "model_load_completed",
        model=model_name,
        seconds=round(perf_counter() - started_at, 3),
    )


def _rerank_with_worker(
    worker: Any,
    query: str,
    documents: list[str],
) -> dict[str, Any]:
    _validate_request(query, documents)
    request_id = uuid4().hex[:12]
    started_at = perf_counter()
    _worker_log(
        "request_started",
        request_id=request_id,
        model=worker.model_name,
        query_chars=len(query),
        document_count=len(documents),
    )
    try:
        scores = worker.model.predict(
            [(query, document) for document in documents],
            batch_size=worker.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
    except Exception as error:
        _worker_log(
            "request_failed",
            request_id=request_id,
            model=worker.model_name,
            error_type=type(error).__name__,
            error=str(error),
        )
        raise

    result = {
        "model": worker.model_name,
        "scores": [float(score) for score in scores],
    }
    _worker_log(
        "request_completed",
        request_id=request_id,
        model=worker.model_name,
        document_count=len(documents),
        seconds=round(perf_counter() - started_at, 3),
    )
    return result


def _release_worker(worker: Any) -> dict[str, str]:
    """Discard cross-encoder state after a batch reranking phase."""
    if hasattr(worker, "model"):
        del worker.model
    gc.collect()
    import torch

    torch.cuda.empty_cache()
    _worker_log("model_released", model=getattr(worker, "model_name", "unknown"))
    return {"model": getattr(worker, "model_name", "unknown"), "status": "released"}


@app.cls(
    image=image,
    gpu="L4",
    timeout=10 * 60,
    scaledown_window=120,
    volumes={"/models": model_cache},
)
class Qwen3Reranker06B:
    """Qwen3 0.6B worker implementing the shared rerank response contract."""

    def _ensure_model(self) -> None:
        if hasattr(self, "model"):
            return
        _load_worker(self, MODEL_NAME_06B, BATCH_SIZE_06B)
        model_cache.commit()

    @modal.enter()
    def load_model(self) -> None:
        self._ensure_model()

    @modal.method()
    def warmup(self) -> dict[str, str]:
        self._ensure_model()
        _worker_log("warmup_completed", model=self.model_name)
        return {"model": self.model_name, "status": "ready"}

    @modal.method()
    def release(self) -> dict[str, str]:
        return _release_worker(self)

    @modal.method()
    def rerank(self, query: str, documents: list[str]) -> dict[str, Any]:
        self._ensure_model()
        return _rerank_with_worker(self, query, documents)


@app.cls(
    image=image,
    gpu="L4",
    timeout=10 * 60,
    scaledown_window=120,
    volumes={"/models": model_cache},
)
class Qwen3Reranker4B:
    """Qwen3 4B worker implementing the shared rerank response contract."""

    def _ensure_model(self) -> None:
        if hasattr(self, "model"):
            return
        _load_worker(self, MODEL_NAME_4B, BATCH_SIZE_4B)
        model_cache.commit()

    @modal.enter()
    def load_model(self) -> None:
        self._ensure_model()

    @modal.method()
    def warmup(self) -> dict[str, str]:
        self._ensure_model()
        _worker_log("warmup_completed", model=self.model_name)
        return {"model": self.model_name, "status": "ready"}

    @modal.method()
    def release(self) -> dict[str, str]:
        return _release_worker(self)

    @modal.method()
    def rerank(self, query: str, documents: list[str]) -> dict[str, Any]:
        self._ensure_model()
        return _rerank_with_worker(self, query, documents)
