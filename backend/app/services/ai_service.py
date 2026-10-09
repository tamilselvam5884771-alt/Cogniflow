import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AIService:
    """Service interface for AI chat generation.

    Provides a temporary mock response implementation for Step 2.
    Decoupled from routing logic so it can be replaced with Google Gemini API
    in subsequent steps.
    """

    async def generate_reply(
        self, message: str, session_id: Optional[str] = None
    ) -> str:
        """Generate an assistant reply for the user's message.

        Args:
            message: The validated and sanitized user message.
            session_id: Optional conversation session identifier.

        Returns:
            str: Assistant response message.
        """
        logger.info("Generating mock AI reply for session_id=%s", session_id)
        # Temporary mock response matching specification
        return "Hello! How can I help you?"


def get_ai_service() -> AIService:
    """FastAPI dependency provider returning an AIService instance."""
    return AIService()
