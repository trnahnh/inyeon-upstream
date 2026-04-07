import asyncio
import hmac
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.core.config import settings
from backend.core.dependencies import get_llm_provider
from backend.core.logging import logger
from backend.routers import analyze, changelog, commit, agent, conflict, pr, rag, split


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    redirect_slashes=False,
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials="*" not in origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class APIKeyMiddleware(BaseHTTPMiddleware):
    OPEN_PATHS = {"/health", "/", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        if not settings.api_key:
            return await call_next(request)

        if request.method == "OPTIONS" or request.url.path in self.OPEN_PATHS:
            return await call_next(request)

        key = request.headers.get("X-API-Key", "")
        if not hmac.compare_digest(key, settings.api_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rpm: int = 30):
        super().__init__(app)
        self.rpm = rpm
        self._requests: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()
        self._last_prune = 0.0

    async def dispatch(self, request: Request, call_next):
        if self.rpm <= 0 or request.method == "OPTIONS" or not request.url.path.startswith("/api/"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - 60

        async with self._lock:
            # Prune stale IPs every 5 minutes
            if now - self._last_prune > 300:
                stale = [ip for ip, ts in self._requests.items() if not ts or ts[-1] < window_start]
                for ip in stale:
                    del self._requests[ip]
                self._last_prune = now

            reqs = self._requests.get(client_ip, [])
            reqs = [t for t in reqs if t > window_start]

            if len(reqs) >= self.rpm:
                self._requests[client_ip] = reqs
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                )

            reqs.append(now)
            self._requests[client_ip] = reqs

        return await call_next(request)


app.add_middleware(APIKeyMiddleware)
app.add_middleware(RateLimitMiddleware, rpm=settings.rate_limit_rpm)

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


@app.get("/providers", tags=["health"])
async def list_providers():
    available = []
    if settings.gemini_api_key:
        available.append({"name": "gemini", "model": settings.gemini_model})
    if settings.openai_api_key:
        available.append({"name": "openai", "model": settings.openai_model})
    available.append({"name": "ollama", "model": settings.ollama_model})
    return {
        "default": settings.llm_provider,
        "available": available,
    }


@app.get("/", tags=["root"])
async def root():
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health",
    }
