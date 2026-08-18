"""Ingest embedding-record JSON files into the local pgvector database."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from sentence_transformers import SentenceTransformer

from .db import PgVectorStore, VECTOR_DIMENSIONS


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_DIR = REPOSITORY_ROOT / "data" / "subject_embed"
DEFAULT_MODEL = "AITeamVN/Vietnamese_Embedding"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_records(source_path: Path) -> tuple[dict, list[dict]]:
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    records = payload.get("embedding_records")
    if not isinstance(records, list) or not records:
        raise ValueError("embedding_records must be a non-empty list")
    return payload, records


def get_source_paths(source: Path | None) -> list[Path]:
    if source is not None:
        if not source.is_file():
            raise ValueError(f"Source JSON file does not exist: {source}")
        return [source]

    source_paths = sorted(DEFAULT_SOURCE_DIR.glob("*.json"))
    if not source_paths:
        raise ValueError(f"No JSON files found in: {DEFAULT_SOURCE_DIR}")
    return source_paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        help="Ingest only this JSON file; defaults to every JSON file in data/subject_embed",
    )
    parser.add_argument(
        "--book-id",
        help="Overrides the top-level book_id in the source JSON",
    )
    parser.add_argument(
        "--mode",
        choices=("append", "replace"),
        default=None,
        help=(
            "For --source: append (default) keeps existing sections, while "
            "replace clears the selected book first. Full-folder ingestion "
            "defaults to replace."
        ),
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--device", default=None, help="cpu, cuda, or omit for auto")
    parser.add_argument(
        "--dsn",
        default=os.getenv("RAG_DATABASE_URL"),
        help="PostgreSQL DSN; defaults to RAG_DATABASE_URL",
    )
    args = parser.parse_args()

    if not args.dsn:
        parser.error("Set RAG_DATABASE_URL or pass --dsn")

    try:
        source_paths = get_source_paths(args.source)
    except ValueError as error:
        parser.error(str(error))

    if args.book_id and len(source_paths) != 1:
        parser.error("--book-id can only be used together with --source")

    mode = args.mode or ("append" if args.source else "replace")
    source_data: list[tuple[Path, list[dict], str]] = []
    for source_path in source_paths:
        payload, records = load_records(source_path)
        book_id = args.book_id or payload.get("book_id")
        if not book_id:
            raise ValueError(
                f"Add top-level book_id to {source_path} or pass --book-id with --source"
            )
        source_data.append((source_path, records, book_id))

    model = SentenceTransformer(args.model, device=args.device)
    model.max_seq_length = 2048

    store = PgVectorStore(args.dsn)
    store.initialize()
    if mode == "replace":
        for book_id in sorted({book_id for _, _, book_id in source_data}):
            deleted_count = store.delete_book_sections(book_id)
            print(f"Removed {deleted_count} existing sections for book_id={book_id}")

    total_records = 0
    for source_path, records, book_id in source_data:
        texts = [record["text_for_embedding"] for record in records]
        vectors = model.encode(
            texts,
            batch_size=8,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=True,
        )
        if vectors.shape != (len(records), VECTOR_DIMENSIONS):
            raise ValueError(
                f"Expected ({len(records)}, {VECTOR_DIMENSIONS}) vectors; got {vectors.shape}"
            )

        for record, vector in zip(records, vectors):
            store.upsert_section(
                book_id=book_id,
                record=record,
                embedding=vector.tolist(),
                content_sha256=sha256_text(record["text_for_embedding"]),
            )
        total_records += len(records)
        print(
            f"Ingested {len(records)} sections from {source_path.name} "
            f"for book_id={book_id}"
        )

    print(
        f"Ingested {total_records} sections from {len(source_paths)} file(s) "
        f"with mode={mode}"
    )


if __name__ == "__main__":
    main()
