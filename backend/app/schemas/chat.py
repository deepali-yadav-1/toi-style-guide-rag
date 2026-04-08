from datetime import datetime

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str = Field(min_length=1, max_length=6000)


class SourceChunk(BaseModel):
    id: str
    document_name: str
    page_number: int
    chunk_index: int
    content: str
    similarity: float


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    history: list[Message] = Field(default_factory=list)
    top_k: int | None = Field(default=None, ge=1, le=12)


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    retrieved_at: datetime


class IngestRequest(BaseModel):
    file_paths: list[str] | None = None
    reset_existing: bool = False


class IngestedDocument(BaseModel):
    document_name: str
    chunks_inserted: int


class IngestResponse(BaseModel):
    processed_files: list[IngestedDocument]
    total_chunks_inserted: int


class HealthResponse(BaseModel):
    status: str


class StatusResponse(BaseModel):
    status: str
    documents_indexed: int
    chunks_indexed: int
    openai_configured: bool
