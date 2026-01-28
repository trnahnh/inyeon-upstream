from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.dependencies import get_ollama_client
from backend.routers import analyze, commit


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    client = get_ollama_client()
    if await client.is_healthy():
        print(f"Connected to Ollama at {settings.ollama_url}")
        print(f"Using model: {settings.ollama_model}")
    else:
        print(f"Warning: Ollama not reachable at {settings.ollama_url}")

    yield

    # Shutdown
    print("Shutting down Inyeon API...")


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Git workflow AI assistant - diff analysis and commit generation",
    lifespan=lifespan,
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(analyze.router, prefix="/api/v1", tags=["analyze"])
app.include_router(commit.router, prefix="/api/v1", tags=["commit"])


@app.get("/health", tags=["health"])
async def health_check():
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
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health",
    }
