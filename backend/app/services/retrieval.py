from __future__ import annotations

import re

from openai import APIConnectionError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.chat import SourceChunk
from app.services.database import database
from app.services.embeddings import embed_texts, embedding_to_vector_literal


settings = get_settings()
logger = get_logger(__name__)
FOCUS_TERM_PATTERN = re.compile(r"'([^']+)'|\"([^\"]+)\"")
COMMON_FOCUS_TERMS = {"a", "an", "the"}
STOPWORDS = {
    "a", "an", "the", "about", "brief", "explain", "tell", "me", "of", "for",
    "to", "and", "or", "in", "on", "with", "how", "does", "should", "be", "used",
    "what", "is", "are", "was", "were", "by",
}
RRF_K = 60


def normalize_text(value: str) -> str:
    return value.lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')


def term_variants(term: str) -> list[str]:
    variants = [term]
    if term.endswith("y") and len(term) > 3:
        variants.append(term[:-1] + "ies")
    elif not term.endswith("s"):
        variants.append(term + "s")
    if term.endswith("ing") and len(term) > 5:
        variants.append(term[:-3])
    return list(dict.fromkeys(variants))


def extract_focus_terms(query: str) -> list[str]:
    quoted_terms = []
    for match in FOCUS_TERM_PATTERN.findall(query):
        term = next((part.strip() for part in match if part.strip()), "")
        if term:
            quoted_terms.append(term)

    lowercase_query = query.lower()
    explicit_terms = [
        term for term in COMMON_FOCUS_TERMS if re.search(rf"\b{re.escape(term)}\b", lowercase_query)
    ]

    ordered_terms: list[str] = []
    for term in quoted_terms + explicit_terms:
        normalized = term.strip()
        if normalized and normalized.lower() not in {item.lower() for item in ordered_terms}:
            ordered_terms.append(normalized)

    return ordered_terms


async def fetch_keyword_matches(term: str, limit: int) -> list[SourceChunk]:
    normalized_term = normalize_text(term)
    pattern = rf"\m{re.escape(normalized_term)}\M"
    rows = await database.pool.fetch(
        """
        SELECT
            id,
            document_name,
            page_number,
            chunk_index,
            content
        FROM document_chunks
        WHERE lower(replace(replace(content, '’', ''''), '‘', '''')) ~ $1
        ORDER BY page_number, chunk_index
        LIMIT $2
        """,
        pattern,
        limit,
    )

    return [
        SourceChunk(
            id=str(row["id"]),
            document_name=row["document_name"],
            page_number=row["page_number"],
            chunk_index=row["chunk_index"],
            content=row["content"],
            similarity=1.0,
        )
        for row in rows
    ]


def extract_significant_terms(query: str) -> list[str]:
    normalized_query = normalize_text(query)
    candidates = re.findall(r"[a-zA-Z][a-zA-Z']+", normalized_query)
    ordered_terms: list[str] = []
    for term in candidates:
        if len(term) < 3:
            continue
        if term in STOPWORDS:
            continue
        if term not in ordered_terms:
            ordered_terms.append(term)
    return ordered_terms


async def fetch_lexical_matches(query: str, limit: int) -> list[SourceChunk]:
    significant_terms = extract_significant_terms(query)[:6]
    ordered_phrase = "%" + "%".join(significant_terms[:4]) + "%" if significant_terms else None
    search_terms: list[str] = []
    for term in significant_terms:
        search_terms.extend(term_variants(term))
    search_terms = list(dict.fromkeys(search_terms))

    rows = await database.pool.fetch(
        """
        WITH ranked AS (
            SELECT
                id,
                document_name,
                page_number,
                chunk_index,
                content,
                (
                    CASE
                        WHEN $1::text IS NOT NULL
                         AND lower(replace(replace(content, '’', ''''), '‘', '''')) LIKE $1
                        THEN 5
                        ELSE 0
                    END
                ) +
                (
                    CASE
                        WHEN cardinality($3::text[]) > 0
                         AND EXISTS (
                            SELECT 1
                            FROM unnest($3::text[]) AS term
                            WHERE split_part(lower(replace(replace(content, '’', ''''), '‘', '''')), '.', 1) LIKE '%' || term || '%'
                        )
                        THEN 3
                        ELSE 0
                    END
                ) +
                (
                    SELECT COALESCE(SUM(
                        CASE
                            WHEN lower(replace(replace(content, '’', ''''), '‘', '''')) LIKE '%' || term || '%'
                            THEN 1
                            ELSE 0
                        END
                    ), 0)
                    FROM unnest($2::text[]) AS term
                ) AS lexical_score
            FROM document_chunks
        )
        SELECT
            id,
            document_name,
            page_number,
            chunk_index,
            content,
            lexical_score
        FROM ranked
        WHERE lexical_score > 0
        ORDER BY lexical_score DESC, page_number, chunk_index
        LIMIT $4
        """,
        ordered_phrase,
        search_terms,
        search_terms,
        limit,
    )

    return [
        SourceChunk(
            id=str(row["id"]),
            document_name=row["document_name"],
            page_number=row["page_number"],
            chunk_index=row["chunk_index"],
            content=row["content"],
            similarity=float(row["lexical_score"]),
        )
        for row in rows
    ]


async def retrieve_chunks(query: str, top_k: int | None = None) -> list[SourceChunk]:
    effective_top_k = top_k or settings.retrieval_top_k
    focus_terms = extract_focus_terms(query)
    keyword_results: list[SourceChunk] = []
    for term in focus_terms[:4]:
        keyword_results.extend(await fetch_keyword_matches(term, 2))
    lexical_results = await fetch_lexical_matches(query, max(effective_top_k * 3, 8))
    semantic_results: list[SourceChunk] = []

    try:
        query_embedding = (await embed_texts([query]))[0]
        vector_literal = embedding_to_vector_literal(query_embedding)

        rows = await database.pool.fetch(
            """
            SELECT
                id,
                document_name,
                page_number,
                chunk_index,
                content,
                1 - (embedding <=> $1::vector) AS similarity
            FROM document_chunks
            ORDER BY embedding <=> $1::vector
            LIMIT $2
            """,
            vector_literal,
            max(effective_top_k * 3, 8),
        )

        semantic_results = [
            SourceChunk(
                id=str(row["id"]),
                document_name=row["document_name"],
                page_number=row["page_number"],
                chunk_index=row["chunk_index"],
                content=row["content"],
                similarity=float(row["similarity"]),
            )
            for row in rows
        ]
    except APIConnectionError as exc:
        logger.warning(
            "Embedding retrieval failed for query %r. Falling back to lexical retrieval only. Error: %s",
            query,
            exc,
        )

    merged: dict[str, SourceChunk] = {}
    hybrid_scores: dict[str, float] = {}
    keyword_ids = {source.id for source in keyword_results}

    def upsert_source(source: SourceChunk) -> None:
        existing = merged.get(source.id)
        if existing is None or source.similarity > existing.similarity:
            merged[source.id] = source

    def apply_rank_scores(sources: list[SourceChunk], weight: float) -> None:
        for rank, source in enumerate(sources, start=1):
            upsert_source(source)
            hybrid_scores[source.id] = hybrid_scores.get(source.id, 0.0) + weight / (RRF_K + rank)

    apply_rank_scores(keyword_results, 3.0)
    apply_rank_scores(lexical_results, 2.0)
    apply_rank_scores(semantic_results, 1.5)

    prioritized_sources = list(merged.values())
    prioritized_sources.sort(
        key=lambda source: (
            0 if source.id in keyword_ids else 1,
            0 if any(re.search(rf"\b{re.escape(term.lower())}\b", normalize_text(source.content)) for term in focus_terms) else 1,
            -hybrid_scores.get(source.id, 0.0),
            -source.similarity,
            source.document_name,
            source.page_number,
            source.chunk_index,
        )
    )

    return prioritized_sources[:effective_top_k]
