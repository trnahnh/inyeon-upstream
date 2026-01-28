from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.dependencies import get_ollama_client
from backend.core.logging import logger
from backend.routers import analyze, commit


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Inyeon API...")
    client = get_ollama_client()

    if await client.is_healthy():
        logger.info(f"Connected to Ollama at {settings.ollama_url}")
        logger.info(f"Using model: {settings.ollama_model}")
    else:
        logger.warning(f"Ollama not reachable at {settings.ollama_url}")

    yield

    # Shutdown
    logger.info("Shutting down Inyeon API...")


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Git workflow AI assistant - diff analysis and commit generation",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(analyze.router, prefix="/api/v1", tags=["analyze"])
app.include_router(commit.router, prefix="/api/v1", tags=["commit"])


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    client = get_ollama_client()
    ollama_healthy = await client.is_healthy()

    return {
        "status": "healthy" if ollama_healthy else "degraded",
        "version": settings.api_version,
        "ollama": {
            "connected": ollama_healthy,
            "url": settings.ollama_url,
            "model": settings.ollama_model,
        },
    }


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health",
    }
