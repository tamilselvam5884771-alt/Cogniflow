import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment or .env file."""

    APP_NAME: str = "College Rules RAG Chatbot"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Google Gemini API key configuration
    GEMINI_API_KEY: str = ""

    # College Rules PDF Configuration
    COLLEGE_RULES_PDF: str = "backend/data/college_rules.pdf"

    # RAG & Retrieval Parameters
    EMBEDDING_MODEL: str = "gemini-embedding-2"
    CHAT_MODEL: str = "gemini-3.5-flash-lite"
    TOP_K_RETRIEVAL: int = 4
    SIMILARITY_THRESHOLD: float = 0.58  # Cosine similarity threshold for relevance filtering

    # PDF Processing Parameters
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB max limit
    DEFAULT_CHUNK_SIZE: int = 1400
    DEFAULT_CHUNK_OVERLAP: int = 200
    MIN_EXTRACTABLE_TEXT_CHARS: int = 50  # Threshold for scanned/empty PDF detection

    # Local Cache / Storage Directory
    DATA_DIR: str = "backend/data"

    def resolve_data_dir(self) -> Path:
        """Resolve the data storage directory to an absolute Path."""
        backend_dir = Path(__file__).resolve().parent.parent
        data_path = backend_dir / "data"
        data_path.mkdir(parents=True, exist_ok=True)
        return data_path

    # Frontend CORS origins allowed to communicate with this backend
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def resolve_pdf_path(self) -> Path:
        """Resolve the configured COLLEGE_RULES_PDF to an absolute Path.

        Checks relative to current working directory, relative to backend,
        and relative to project workspace root.
        """
        raw_path = Path(self.COLLEGE_RULES_PDF)
        if raw_path.is_absolute() and raw_path.is_file():
            return raw_path

        # 1. Check relative to current working directory
        if raw_path.is_file():
            return raw_path.resolve()

        # 2. Check relative to backend directory
        backend_dir = Path(__file__).resolve().parent.parent
        backend_path = backend_dir / raw_path.name
        if backend_path.is_file():
            return backend_path.resolve()

        backend_data_path = backend_dir / "data" / raw_path.name
        if backend_data_path.is_file():
            return backend_data_path.resolve()

        # 3. Check relative to workspace root (parent of backend)
        workspace_dir = backend_dir.parent
        workspace_path = workspace_dir / self.COLLEGE_RULES_PDF
        if workspace_path.is_file():
            return workspace_path.resolve()

        # Return default resolved path even if not yet created for clean error reporting
        return (backend_dir / "data" / raw_path.name).resolve()


settings = Settings()
