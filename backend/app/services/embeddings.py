from __future__ import annotations

import asyncio

from openai import APIConnectionError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm_client import get_openai_client


settings = get_settings()
logger = get_logger(__name__)


def embedding_to_vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(f"{value:.10f}" for value in embedding) + "]"


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    results: list[list[float]] = []

    for start in range(0, len(texts), settings.embedding_batch_size):
        batch = texts[start : start + settings.embedding_batch_size]
        response = await _embed_batch_with_retry(batch, start)
        results.extend(item.embedding for item in response.data)

    return results


async def _embed_batch_with_retry(batch: list[str], batch_start: int):
    max_attempts = 4

    for attempt in range(1, max_attempts + 1):
        try:
            return await get_openai_client().embeddings.create(
                model=settings.openai_embedding_model,
                input=batch,
            )
        except APIConnectionError:
            if attempt == max_attempts:
                raise
            delay_seconds = min(2 ** attempt, 8)
            logger.warning(
                "Embedding batch starting at index %s failed on attempt %s/%s. Retrying in %s seconds.",
                batch_start,
                attempt,
                max_attempts,
                delay_seconds,
            )
            await asyncio.sleep(delay_seconds)
