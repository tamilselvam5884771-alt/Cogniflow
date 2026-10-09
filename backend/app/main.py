import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.chat import router as chat_router
from app.schemas import HealthResponse
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)

# Track startup diagnostic status
startup_status: dict = {
    "initialized": False,
    "error": None,
    "pdf_path": None,
    "chunks_indexed": 0,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown procedures."""
    pdf_path = settings.resolve_pdf_path()
    startup_status["pdf_path"] = str(pdf_path)

    if not pdf_path.is_file():
        err = f"College rules PDF file not found at '{pdf_path}'."
        startup_status["error"] = err
        logger.error(err)
    else:
        # Check API key configuration before attempting embedding
        api_key = settings.GEMINI_API_KEY.strip()
        if not api_key or api_key == "your_gemini_api_key_here":
            err = "GEMINI_API_KEY is not configured in backend/.env. RAG embedding and generation are pending API key configuration."
            startup_status["error"] = err
            logger.warning(err)
        else:
            try:
                count = ai_service.load_and_index_college_rules(pdf_path)
                startup_status["initialized"] = True
                startup_status["chunks_indexed"] = count
                startup_status["error"] = None
                logger.info(
                    "Successfully indexed %d chunks from college rules PDF '%s'",
                    count,
                    pdf_path.name,
                )
            except Exception as exc:
                err = f"Failed to index college rules PDF: {exc}"
                startup_status["error"] = err
                logger.error(err, exc_info=True)

    yield


# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API for College Rules RAG Chatbot powered by Google Gemini, FAISS, and FastAPI.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure Cross-Origin Resource Sharing (CORS) for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(chat_router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint welcoming visitors with API info and docs link."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "health_url": "/api/health",
        "pdf_indexed": ai_service.vector_store.is_indexed(),
    }


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check endpoint",
)
async def health_check():
    """Health check endpoint to verify backend service operational status."""
    return HealthResponse(
        status="ok",
        message="AI Chatbot backend is up and running!",
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        pdf_indexed=ai_service.vector_store.is_indexed(),
        total_chunks=ai_service.vector_store.count(),
    )
