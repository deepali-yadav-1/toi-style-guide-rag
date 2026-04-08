from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.chat import IngestRequest, IngestResponse, IngestedDocument
from app.services.chunking import split_into_chunks
from app.services.database import database
from app.services.embeddings import embed_texts, embedding_to_vector_literal
from app.services.pdf_loader import extract_pages


settings = get_settings()
logger = get_logger(__name__)


def resolve_input_paths(file_paths: list[str] | None) -> list[Path]:
    base_dir = settings.documents_dir.resolve()
    if file_paths:
        resolved = [Path(path).resolve() for path in file_paths]
    else:
        resolved = sorted(base_dir.glob("*.pdf"))

    if not resolved:
        raise FileNotFoundError("No PDF files were found for ingestion.")

    missing = [str(path) for path in resolved if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing files: {', '.join(missing)}")

    return resolved


async def reset_documents_table() -> None:
    await database.pool.execute("TRUNCATE TABLE document_chunks RESTART IDENTITY")


async def ingest_documents(payload: IngestRequest) -> IngestResponse:
    pdf_paths = resolve_input_paths(payload.file_paths)

    if payload.reset_existing:
        await reset_documents_table()

    processed_files: list[IngestedDocument] = []
    total_inserted = 0

    for pdf_path in pdf_paths:
        pages = extract_pages(pdf_path)
        insert_rows: list[tuple[str, str, int, int, str, str]] = []

        for page in pages:
            chunks = split_into_chunks(str(page["text"]))
            for chunk_index, chunk_text in enumerate(chunks):
                chunk_hash = hashlib.sha256(
                    f"{pdf_path.name}:{page['page_number']}:{chunk_index}:{chunk_text}".encode("utf-8")
                ).hexdigest()
                insert_rows.append(
                    (
                        chunk_hash,
                        pdf_path.name,
                        int(page["page_number"]),
                        chunk_index,
                        chunk_text,
                        chunk_hash,
                    )
                )

        if not insert_rows:
            logger.warning("No chunks extracted from %s", pdf_path.name)
            processed_files.append(
                IngestedDocument(document_name=pdf_path.name, chunks_inserted=0)
            )
            continue

        embeddings = await embed_texts([row[4] for row in insert_rows])
        inserted_for_file = 0

        async with database.pool.acquire() as connection:
            async with connection.transaction():
                for row, embedding in zip(insert_rows, embeddings, strict=True):
                    result = await connection.execute(
                        """
                        INSERT INTO document_chunks (
                            chunk_hash,
                            document_name,
                            page_number,
                            chunk_index,
                            content,
                            embedding
                        )
                        VALUES ($1, $2, $3, $4, $5, $6::vector)
                        ON CONFLICT (chunk_hash) DO NOTHING
                        """,
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        embedding_to_vector_literal(embedding),
                    )
                    if result.endswith("1"):
                        inserted_for_file += 1

        processed_files.append(
            IngestedDocument(
                document_name=pdf_path.name,
                chunks_inserted=inserted_for_file,
            )
        )
        total_inserted += inserted_for_file
        logger.info("Ingested %s chunks from %s", inserted_for_file, pdf_path.name)

    return IngestResponse(
        processed_files=processed_files,
        total_chunks_inserted=total_inserted,
    )
