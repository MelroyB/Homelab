from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.init_db import seed_services
from app.db.session import SessionLocal
from app.models import audit, auth, backup, service, user  # noqa: F401

settings = get_settings()
configure_logging(settings)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    with SessionLocal() as db:
        try:
            seed_services(db)
        except Exception as exc:
            logger.exception(
                "Startup failed while seeding services. Ensure DB migrations are applied.",
                exc_info=exc,
            )
            raise
    yield


app = FastAPI(
    title="Homelab Control Plane API",
    version="0.1.0",
    description="API-first backend for homelab service orchestration",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:4173",
        "http://localhost:8080",
        "http://127.0.0.1:4173",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_EXEMPT_PREFIXES = (
    "/api/v1/auth/login",
    "/api/v1/bootstrap",
    "/api/v1/health",
    "/docs",
    "/openapi.json",
    "/redoc",
)


@app.middleware("http")
async def csrf_protection_middleware(
    request: Request, call_next: Callable[[Request], Response]
) -> Response:
    if request.method not in SAFE_METHODS and request.url.path.startswith("/api/"):
        if not any(request.url.path.startswith(prefix) for prefix in CSRF_EXEMPT_PREFIXES):
            cookie_token = request.cookies.get("hl_csrf")
            header_token = request.headers.get("x-csrf-token")
            if not cookie_token or not header_token or cookie_token != header_token:
                return Response(
                    content='{"detail":"CSRF token missing or invalid"}',
                    media_type="application/json",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
    return await call_next(request)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "homelab-control-backend", "status": "ok"}


@app.get("/health/live")
def live_health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router)
