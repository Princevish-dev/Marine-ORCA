from __future__ import annotations
import asyncio
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.api import chat, events, marine, health

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orca")

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.guardian.guardian import run_guardian
    if settings.guardian_enabled:
        task = asyncio.create_task(run_guardian())
        logger.info("Guardian started")
    else:
        task = None
    yield
    if task:
        task.cancel()


app = FastAPI(
    title="ORCA — Marine Intelligence API",
    description="Agentic AI marine decision-support platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.demo_mode else None,
    redoc_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

ALLOWED_ORIGINS = [
    settings.frontend_url,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Request-ID"] = str(uuid.uuid4())[:8]
    return response


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    if request.method == "POST":
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 50_000:
            return JSONResponse({"detail": "Request too large"}, status_code=413)
    return await call_next(request)


app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(marine.router, prefix="/api", tags=["marine"])


@app.get("/")
async def root():
    return {
        "service": "ORCA Marine Intelligence",
        "version": "1.0.0",
        "status": "online",
        "demo_mode": settings.demo_mode,
    }
