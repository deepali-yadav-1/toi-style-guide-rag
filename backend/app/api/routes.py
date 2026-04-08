from fastapi import APIRouter, HTTPException, status
from openai import APIConnectionError, APIError
from starlette.responses import StreamingResponse

from app.core.logging import get_logger
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    StatusResponse,
)
from app.services.ingestion import ingest_documents
from app.services.rag import answer_query, sse_event, stream_answer_query
from app.services.status import get_system_status


router = APIRouter()
logger = get_logger(__name__)


@router.get("/health", response_model=HealthResponse)
async def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/status", response_model=StatusResponse)
async def status_check() -> StatusResponse:
    return await get_system_status()


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    try:
        return await answer_query(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except APIConnectionError as exc:
        logger.exception("OpenAI connectivity failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "OpenAI connection failed. Check DNS and proxy settings. "
                "This app now ignores shell proxy variables by default."
            ),
        ) from exc
    except APIError as exc:
        logger.exception("OpenAI request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI request failed: {exc}",
        ) from exc
    except Exception as exc:  # pragma: no cover
        logger.exception("Chat request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate an answer: {exc}",
        ) from exc


@router.post("/chat/stream")
async def chat_stream(payload: ChatRequest) -> StreamingResponse:
    async def event_generator():
        try:
            async for chunk in stream_answer_query(payload):
                yield chunk
        except ValueError as exc:
            yield sse_event("error", {"detail": str(exc)})
        except APIConnectionError as exc:
            logger.exception("OpenAI connectivity failed: %s", exc)
            yield sse_event(
                "error",
                {
                    "detail": (
                        "OpenAI connection failed. Check DNS and proxy settings. "
                        "This app now ignores shell proxy variables by default."
                    )
                },
            )
        except APIError as exc:
            logger.exception("OpenAI request failed: %s", exc)
            yield sse_event("error", {"detail": f"OpenAI request failed: {exc}"})
        except Exception as exc:  # pragma: no cover
            logger.exception("Streaming chat request failed: %s", exc)
            yield sse_event("error", {"detail": f"Failed to generate an answer: {exc}"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/ingest", response_model=IngestResponse)
async def ingest(payload: IngestRequest) -> IngestResponse:
    try:
        return await ingest_documents(payload)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except APIConnectionError as exc:
        logger.exception("OpenAI connectivity failed during ingestion: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "OpenAI connection failed during ingestion. Check DNS and proxy "
                "settings. This app now ignores shell proxy variables by default."
            ),
        ) from exc
    except APIError as exc:
        logger.exception("OpenAI request failed during ingestion: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI request failed during ingestion: {exc}",
        ) from exc
    except Exception as exc:  # pragma: no cover
        logger.exception("Ingestion failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest documents: {exc}",
        ) from exc
