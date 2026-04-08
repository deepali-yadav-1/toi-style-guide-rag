from __future__ import annotations

import json
from datetime import datetime, timezone

from app.core.config import get_settings
from app.schemas.chat import ChatRequest, ChatResponse, Message
from app.services.llm_client import get_openai_client
from app.services.retrieval import retrieve_chunks


settings = get_settings()

SYSTEM_PROMPT = """You are a careful assistant for the Times of India style guide and glossary.
Answer only with support from the retrieved context.
If the answer is not in the provided context, say that the documents do not contain enough information.
Prefer concise, editorially precise answers.
When useful, mention the source document and page number naturally.
If the user asks about multiple terms or subquestions, address each one explicitly."""


def trim_history(history: list[Message]) -> list[Message]:
    return history[-settings.max_chat_history_messages :]


def build_context_block(sources: list) -> str:
    return "\n\n".join(
        f"[Source {index}] {source.document_name} | page {source.page_number} | chunk {source.chunk_index}\n"
        f"{source.content}"
        for index, source in enumerate(sources, start=1)
    )


async def prepare_rag_context(payload: ChatRequest) -> tuple[list, list[dict[str, str]]]:
    sources = await retrieve_chunks(payload.query, payload.top_k)
    if not sources:
        raise ValueError("No source chunks were found. Run ingestion first.")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(message.model_dump() for message in trim_history(payload.history))
    messages.append(
        {
            "role": "user",
            "content": (
                "Use the context below to answer the question.\n\n"
                "Make sure you cover every term or item the user asked about, not just the most prominent one.\n\n"
                f"Context:\n{build_context_block(sources)}\n\n"
                f"Question: {payload.query}"
            ),
        }
    )

    return sources, messages


async def answer_query(payload: ChatRequest) -> ChatResponse:
    sources, messages = await prepare_rag_context(payload)

    completion = await get_openai_client().chat.completions.create(
        model=settings.openai_chat_model,
        temperature=0.1,
        messages=messages,
    )

    answer = completion.choices[0].message.content or (
        "I couldn't generate an answer from the retrieved context."
    )

    return ChatResponse(
        answer=answer.strip(),
        sources=sources,
        retrieved_at=datetime.now(timezone.utc),
    )


async def stream_answer_query(payload: ChatRequest):
    sources, messages = await prepare_rag_context(payload)

    yield sse_event(
        "sources",
        {
            "sources": [source.model_dump() for source in sources],
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    stream = await get_openai_client().chat.completions.create(
        model=settings.openai_chat_model,
        temperature=0.1,
        messages=messages,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield sse_event("token", {"token": delta})

    yield sse_event("done", {"status": "completed"})


def sse_event(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"
