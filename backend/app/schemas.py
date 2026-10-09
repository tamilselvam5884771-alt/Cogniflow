import uuid
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    """Schema for GET /api/health endpoint response."""

    status: str = Field(default="ok", description="Operational status of the API")
    message: str = Field(
        default="AI Chatbot backend is up and running!",
        description="Informational status message",
    )
    version: str = Field(default="0.1.0", description="API version")
    environment: str = Field(
        default="development", description="Current runtime environment"
    )


class ChatRequest(BaseModel):
    """Schema for POST /api/chat endpoint request."""

    message: str = Field(
        ...,
        description="User message text to be processed by the chatbot",
        examples=["Hello, how are you?"],
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional conversation session ID. If omitted or null, one will be generated.",
        examples=["session-123e4567-e89b-12d3-a456-426614174000"],
    )

    @field_validator("message", mode="before")
    @classmethod
    def validate_message(cls, v: object) -> str:
        """Validate and sanitize user message:
        - Must be a string.
        - Strips leading and trailing whitespace.
        - Rejects empty strings or whitespace-only messages.
        - Limits message length to 4000 characters.
        """
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
        description="Assistant reply text generated for the conversation",
        examples=["Hello! How can I help you?"],
    )
    session_id: str = Field(
        ...,
        description="Conversation session ID associated with this turn",
        examples=["session-123e4567-e89b-12d3-a456-426614174000"],
    )
