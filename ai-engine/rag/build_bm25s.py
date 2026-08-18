"""Build one BM25s index from embedding-record JSON files."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import bm25s
from bm25s.tokenization import Tokenizer


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_DIR = REPOSITORY_ROOT / "data" / "subject_embed"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "artifacts" / "bm25s"
TOKENIZER_SPLITTER = r"(?u)\b\w+\b"


def source_key(path: Path) -> str:
    resolved_path = path.resolve()
    try:
        return resolved_path.relative_to(REPOSITORY_ROOT).as_posix()
    except ValueError:
        return str(resolved_path)


def load_source(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    book_id = payload.get("book_id")
    records = payload.get("embedding_records")
    if not isinstance(book_id, str) or not book_id:
        raise ValueError(f"{path}: missing non-empty top-level book_id")
    if not isinstance(records, list) or not records:
        raise ValueError(f"{path}: embedding_records must be a non-empty list")

    documents: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"{path}: each embedding record must be an object")
        section_id = record.get("id")
        content = record.get("text_for_embedding")
        metadata = record.get("metadata")
        if not isinstance(section_id, str) or not section_id:
            raise ValueError(f"{path}: record has missing id")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"{path}: {section_id} has empty text_for_embedding")
        if not isinstance(metadata, dict):
            raise ValueError(f"{path}: {section_id} has invalid metadata")
        documents.append(
            {
                "book_id": book_id,
                "section_id": section_id,
                "content": content,
                "metadata": metadata,
                "source_file": source_key(path),
            }
        )
    return documents


def load_documents(path: Path) -> list[dict[str, Any]]:
    documents_path = path / "documents.jsonl"
    if not documents_path.is_file():
        return []
    with documents_path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def ensure_unique_documents(documents: list[dict[str, Any]]) -> None:
    seen: set[tuple[str, str]] = set()
    duplicates: list[str] = []
    for document in documents:
        key = (document["book_id"], document["section_id"])
        if key in seen:
            duplicates.append(f"{key[0]}/{key[1]}")
        seen.add(key)
    if duplicates:
        raise ValueError(
            "Duplicate (book_id, section_id): " + ", ".join(sorted(set(duplicates)))
        )


def write_documents(path: Path, documents: list[dict[str, Any]]) -> None:
    with (path / "documents.jsonl").open("w", encoding="utf-8") as file:
        for document in documents:
            file.write(json.dumps(document, ensure_ascii=False, sort_keys=True))
            file.write("\n")


def replace_directory(staging_dir: Path, output_dir: Path) -> None:
    backup_dir = output_dir.with_name(f"{output_dir.name}.previous")
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    if output_dir.exists():
        output_dir.rename(backup_dir)
    try:
        staging_dir.rename(output_dir)
    except Exception:
        if backup_dir.exists():
            backup_dir.rename(output_dir)
        raise
    shutil.rmtree(backup_dir, ignore_errors=True)


def build_index(documents: list[dict[str, Any]], output_dir: Path) -> None:
    ensure_unique_documents(documents)
    if not documents:
        raise ValueError("Cannot build an empty BM25s index")

    staging_dir = output_dir.with_name(f"{output_dir.name}.building")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)

    tokenizer = Tokenizer(
        lower=True,
        splitter=TOKENIZER_SPLITTER,
        stopwords=[],
        stemmer=None,
    )
    tokens = tokenizer.tokenize(
        [document["content"] for document in documents], return_as="tuple"
    )
    retriever = bm25s.BM25(method="lucene", corpus=documents)
    retriever.index(tokens)
    retriever.save(staging_dir, corpus=documents)
    tokenizer.save_vocab(staging_dir)
    tokenizer.save_stopwords(staging_dir)
    write_documents(staging_dir, documents)

    source_files = sorted({document["source_file"] for document in documents})
    manifest = {
        "schema_version": 1,
        "engine": "bm25s",
        "method": "lucene",
        "document_count": len(documents),
        "source_files": source_files,
        "tokenizer": {
            "lower": True,
            "splitter": TOKENIZER_SPLITTER,
            "stopwords": [],
            "stemmer": None,
        },
    }
    (staging_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    replace_directory(staging_dir, output_dir)


def all_source_paths(source_dir: Path) -> list[Path]:
    paths = sorted(source_dir.glob("*.json"))
    if not paths:
        raise ValueError(f"No JSON files found in: {source_dir}")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        help="Update one JSON file instead of rebuilding from all data/subject_embed files",
    )
    parser.add_argument(
        "--mode",
        choices=("append", "overwrite"),
        help="append adds a new source; overwrite replaces documents from that source",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help=f"Default: {DEFAULT_SOURCE_DIR}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Default: {DEFAULT_OUTPUT_DIR}",
    )
    args = parser.parse_args()

    if args.source is None and args.mode is not None:
        parser.error("--mode requires --source")
    if args.source is not None and args.mode is None:
        parser.error("Choose --mode append or --mode overwrite with --source")

    output_dir = args.output_dir.resolve()
    if args.source is None:
        source_paths = all_source_paths(args.source_dir.resolve())
        documents = []
        for source_path in source_paths:
            documents.extend(load_source(source_path))
        mode_label = "rebuild all sources"
    else:
        source_path = args.source.resolve()
        if not source_path.is_file():
            parser.error(f"Source JSON file does not exist: {source_path}")
        new_documents = load_source(source_path)
        existing_documents = load_documents(output_dir)
        key = source_key(source_path)
        if args.mode == "append":
            if any(document.get("source_file") == key for document in existing_documents):
                parser.error(
                    "This source is already indexed; use --mode overwrite to replace it"
                )
            documents = existing_documents + new_documents
        else:
            documents = [
                document
                for document in existing_documents
                if document.get("source_file") != key
            ] + new_documents
        mode_label = f"{args.mode} {source_path.name}"

    try:
        build_index(documents, output_dir)
    except ValueError as error:
        parser.error(str(error))

    print(
        f"Built BM25s index with {len(documents)} sections "
        f"({mode_label}) at {output_dir}"
    )


if __name__ == "__main__":
    main()
