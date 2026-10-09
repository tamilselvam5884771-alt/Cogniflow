import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import ChatRequest, ChatResponse
from app.services.ai_service import AIService, get_ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a chat message",
    description="Processes a user chat message, manages session context, and returns an assistant response.",
)
async def chat(
    request: ChatRequest,
    ai_service: AIService = Depends(get_ai_service),
) -> ChatResponse:
    """Chat endpoint to process user messages and return an assistant response.

    - **message**: User message string (validated, sanitized, and non-empty).
    - **session_id**: Optional conversation identifier; automatically generated if omitted.
    """
    session_id = request.session_id or str(uuid.uuid4())

    try:
        reply = await ai_service.generate_reply(
            message=request.message,
            session_id=session_id,
        )
        return ChatResponse(
            success=True,
            reply=reply,
            session_id=session_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Unexpected error while processing chat message for session %s: %s",
            session_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request.",
        )
