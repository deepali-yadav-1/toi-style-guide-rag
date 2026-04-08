import asyncio

from app.schemas.chat import IngestRequest
from app.services.database import database
from app.services.ingestion import ingest_documents


async def main() -> None:
    await database.connect()
    try:
        result = await ingest_documents(IngestRequest())
        print(result.model_dump_json(indent=2))
    finally:
        await database.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
