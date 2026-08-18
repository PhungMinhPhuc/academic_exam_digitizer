# ai-engine/rag/db.py
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Sequence

import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb
from psycopg.rows import dict_row

VECTOR_DIMENSIONS = 1024


SCHEMA_SQL = f"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS rag;

CREATE TABLE IF NOT EXISTS rag.sections (
    book_id text NOT NULL,
    section_id text NOT NULL,

    content text NOT NULL,
    content_sha256 char(64) NOT NULL,

    subject text NOT NULL,
    grade smallint NOT NULL,
    chapter_id text NOT NULL,
    lesson_id text NOT NULL,
    metadata jsonb NOT NULL,

    embedding vector({VECTOR_DIMENSIONS}) NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (book_id, section_id)
);

-- Filter metadata
CREATE INDEX IF NOT EXISTS sections_subject_grade_chapter_idx
    ON rag.sections (subject, grade, chapter_id);

CREATE INDEX IF NOT EXISTS sections_book_idx
    ON rag.sections (book_id);

-- Keyword search
-- Chỉ thêm khi corpus tăng lớn
-- CREATE INDEX IF NOT EXISTS sections_embedding_hnsw_idx
--     ON rag.sections
--     USING hnsw (embedding vector_cosine_ops);

-- Remove the legacy FTS branch without deleting sections or embeddings.
DROP FUNCTION IF EXISTS rag.hybrid_search(
    text, vector, integer, text, smallint, text, integer
);
DROP INDEX IF EXISTS rag.sections_fts_idx;
ALTER TABLE rag.sections DROP COLUMN IF EXISTS fts;

CREATE OR REPLACE FUNCTION rag.vector_search(
    query_embedding vector({VECTOR_DIMENSIONS}),
    match_count integer DEFAULT 5,
    filter_subject text DEFAULT NULL,
    filter_grade smallint DEFAULT NULL,
    filter_book_id text DEFAULT NULL
)
RETURNS TABLE (
    book_id text,
    section_id text,
    content text,
    metadata jsonb,
    vector_rank bigint,
    cosine_similarity double precision
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        s.book_id,
        s.section_id,
        s.content,
        s.metadata,
        row_number() OVER (ORDER BY s.embedding <=> query_embedding) AS vector_rank,
        1.0 - (s.embedding <=> query_embedding) AS cosine_similarity
    FROM rag.sections AS s
    WHERE (filter_subject IS NULL OR s.subject = filter_subject)
      AND (filter_grade IS NULL OR s.grade = filter_grade)
      AND (filter_book_id IS NULL OR s.book_id = filter_book_id)
    ORDER BY s.embedding <=> query_embedding
    LIMIT GREATEST(match_count, 1);
$$;
"""


@dataclass
class PgVectorStore:
    dsn: str

    def connect(self):
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(SCHEMA_SQL)
            register_vector(connection)
            connection.commit()

    def upsert_section(
        self,
        book_id: str,
        record: dict[str, Any],
        embedding: list[float],
        content_sha256: str,
    ) -> None:
        metadata = record["metadata"]

        with self.connect() as connection:
            register_vector(connection)

            connection.execute(
                """
                INSERT INTO rag.sections (
                    book_id, section_id, content, content_sha256,
                    subject, grade, chapter_id, lesson_id, metadata, embedding
                )
                VALUES (
                    %(book_id)s, %(section_id)s, %(content)s, %(content_sha256)s,
                    %(subject)s, %(grade)s, %(chapter_id)s, %(lesson_id)s,
                    %(metadata)s, %(embedding)s
                )
                ON CONFLICT (book_id, section_id) DO UPDATE SET
                    content = EXCLUDED.content,
                    content_sha256 = EXCLUDED.content_sha256,
                    subject = EXCLUDED.subject,
                    grade = EXCLUDED.grade,
                    chapter_id = EXCLUDED.chapter_id,
                    lesson_id = EXCLUDED.lesson_id,
                    metadata = EXCLUDED.metadata,
                    embedding = EXCLUDED.embedding,
                    updated_at = now()
                """,
                {
                    "book_id": book_id,
                    "section_id": record["id"],
                    "content": record["text_for_embedding"],
                    "content_sha256": content_sha256,
                    "subject": metadata["subject"],
                    "grade": metadata["grade"],
                    "chapter_id": metadata["chapter_id"],
                    "lesson_id": metadata["lesson_id"],
                    "metadata": Jsonb(metadata),
                    "embedding": Vector(embedding),
                },
            )
            connection.commit()

    def delete_book_sections(self, book_id: str) -> int:
        with self.connect() as connection:
            result = connection.execute(
                "DELETE FROM rag.sections WHERE book_id = %(book_id)s",
                {"book_id": book_id},
            )
            connection.commit()
        return result.rowcount

    def vector_search(
        self,
        query_embedding: Sequence[float],
        match_count: int = 5,
        subject: str | None = None,
        grade: int | None = None,
        book_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if len(query_embedding) != VECTOR_DIMENSIONS:
            raise ValueError(
                f"Expected {VECTOR_DIMENSIONS} embedding dimensions, "
                f"got {len(query_embedding)}"
            )
        with self.connect() as connection:
            register_vector(connection)
            rows = connection.execute(
                """
                SELECT * FROM rag.vector_search(
                    %(query_embedding)s::vector,
                    %(match_count)s::integer,
                    %(subject)s::text,
                    %(grade)s::smallint,
                    %(book_id)s::text
                )
                """,
                {
                    "query_embedding": Vector(query_embedding),
                    "match_count": match_count,
                    "subject": subject,
                    "grade": grade,
                    "book_id": book_id,
                },
            ).fetchall()
        return list(rows)
