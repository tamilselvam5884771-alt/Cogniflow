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
    summary="Query College Rules",
    description="Asks a question about institutional policies and returns an answer grounded strictly in the college rules PDF with page citations.",
)
async def chat(
    request: ChatRequest,
    ai_service: AIService = Depends(get_ai_service),
) -> ChatResponse:
    """Chat endpoint to answer college rules questions with page citations.

    - **message**: User question string.
    - **session_id**: Optional conversation identifier; automatically generated if omitted.
    """
    session_id = request.session_id or str(uuid.uuid4())

    try:
        reply, sources = await ai_service.generate_reply(
            message=request.message,
            session_id=session_id,
        )
        return ChatResponse(
            success=True,
            reply=reply,
            session_id=session_id,
            sources=sources,
            timings=ai_service.last_timings,
        )
    except HTTPException:
        raise
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        err_text = str(exc)
        logger.warning("RAG operational error: %s", err_text)
        if any(keyword in err_text.lower() for keyword in ["not initialized", "not found", "gemini_api_key", "empty", "scanned"]):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=err_text,
            )
        if any(keyword in err_text.lower() for keyword in ["503", "unavailable", "429", "resource_exhausted"]):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The College Rules AI service is temporarily experiencing high demand. Please retry your question in a few moments.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request.",
        )
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
