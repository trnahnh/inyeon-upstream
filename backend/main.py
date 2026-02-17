from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.dependencies import get_llm_provider
from backend.core.logging import logger
from backend.routers import analyze, changelog, commit, agent, conflict, pr, rag, split


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Inyeon API...")
    llm = get_llm_provider()

    if await llm.is_healthy():
        logger.info(f"LLM provider: {settings.llm_provider}")
    else:
        logger.warning("LLM provider not reachable")

    yield

    logger.info("Shutting down Inyeon API...")


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Agentic AI Git Assistant",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api/v1", tags=["analyze"])
app.include_router(commit.router, prefix="/api/v1", tags=["commit"])
app.include_router(agent.router, prefix="/api/v1")
app.include_router(rag.router, prefix="/api/v1/rag")
app.include_router(changelog.router, prefix="/api/v1")
app.include_router(conflict.router, prefix="/api/v1")
app.include_router(pr.router, prefix="/api/v1")
app.include_router(split.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    llm = get_llm_provider()
    llm_healthy = await llm.is_healthy()

    return {
        "status": "healthy" if llm_healthy else "degraded",
        "version": settings.api_version,
        "llm": {
            "provider": settings.llm_provider,
            "connected": llm_healthy,
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
