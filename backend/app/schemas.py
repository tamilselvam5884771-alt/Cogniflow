import uuid
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    """Schema for GET /api/health endpoint response."""

    status: str = Field(default="ok", description="Operational status of the API")
    message: str = Field(
        default="AI Chatbot backend is up and running!",
        description="Informational status message",
    )
    version: str = Field(default="0.2.0", description="API version")
    environment: str = Field(
        default="development", description="Current runtime environment"
    )
    pdf_indexed: bool = Field(
        default=False, description="Whether the college rules PDF is loaded and indexed"
    )
    total_chunks: int = Field(
        default=0, description="Total indexed text chunks available for retrieval"
    )


class CitationSource(BaseModel):
    """Provenance citation linking an answer directly to an extracted PDF page."""

    page_number: int = Field(
        ..., description="1-based page number in the college rules PDF"
    )
    chunk_id: str = Field(
        ..., description="Unique chunk identifier from the vector index"
    )
    snippet: str = Field(
        ..., description="Excerpt text snippet retrieved from this page"
    )
    score: Optional[float] = Field(
        default=None, description="Cosine similarity relevance score"
    )


class ChatRequest(BaseModel):
    """Schema for POST /api/chat endpoint request."""

    message: str = Field(
        ...,
        description="User question regarding college rules and guidelines",
        examples=["What is the minimum attendance requirement for semester exams?"],
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional conversation session ID. If omitted or null, one will be generated.",
        examples=["session-123e4567-e89b-12d3-a456-426614174000"],
    )

    @field_validator("message", mode="before")
    @classmethod
    def validate_message(cls, v: object) -> str:
        """Validate and sanitize user message."""
        if not isinstance(v, str):
            raise ValueError("Message must be a string.")

        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty or contain only whitespace.")

        max_length = 4000
        if len(cleaned) > max_length:
            raise ValueError(f"Message cannot exceed {max_length} characters.")

        return cleaned

    @field_validator("session_id", mode="before")
    @classmethod
    def sanitize_session_id(cls, v: object) -> str:
        """Validate or automatically generate session ID if missing or blank."""
        if v is None:
            return str(uuid.uuid4())

        cleaned = str(v).strip()
        if not cleaned:
            return str(uuid.uuid4())

        return cleaned


class ChatResponse(BaseModel):
    """Schema for POST /api/chat endpoint response."""

    success: bool = Field(
        default=True,
        description="Indicates whether the request was processed successfully",
        examples=[True],
    )
    reply: str = Field(
        ...,
        description="Assistant reply grounded in the college rules handbook",
        examples=[
            "Students must maintain a minimum of 75% attendance to appear for examinations. (Page 12)"
        ],
    )
    session_id: str = Field(
        ...,
        description="Conversation session ID associated with this turn",
        examples=["session-123e4567-e89b-12d3-a456-426614174000"],
    )
    sources: List[CitationSource] = Field(
        default_factory=list,
        description="Verified source citations with page numbers from the college rules PDF",
    )
    timings: Optional[dict] = Field(
        default=None,
        description="Diagnostic stage latencies in seconds (embedding, faiss, context, generation, total)",
    )
