from __future__ import annotations

from app.schemas.chat import StatusResponse
from app.services.database import database


async def get_system_status() -> StatusResponse:
    row = await database.pool.fetchrow(
        """
        SELECT
            COUNT(DISTINCT document_name) AS documents_indexed,
            COUNT(*) AS chunks_indexed
        FROM document_chunks
        """
    )

    documents_indexed = int(row["documents_indexed"] or 0)
    chunks_indexed = int(row["chunks_indexed"] or 0)

    return StatusResponse(
        status="ready" if chunks_indexed > 0 else "needs_ingestion",
        documents_indexed=documents_indexed,
        chunks_indexed=chunks_indexed,
        openai_configured=True,
    )
