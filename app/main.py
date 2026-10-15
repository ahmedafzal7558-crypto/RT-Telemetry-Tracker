"""
FastAPI application entry point for the IoT Telemetry Processing Engine.

Wires together routers, CORS middleware, and startup/shutdown lifecycle events.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.devices import router as devices_router
from app.api.v1.general import router as general_router
from app.api.v1.telemetry import router as telemetry_router
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan:
      - On startup: log readiness.
      - On shutdown: log teardown.
    Table creation is intentionally NOT performed here — the schema is
    managed via Supabase migrations to keep DDL out of application code.
    """
    print(f"[{settings.APP_NAME}] v{settings.APP_VERSION} starting up...")
    yield
    print(f"[{settings.APP_NAME}] shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "A production-ready backend for ingesting, storing, and analyzing "
        "telemetry data from IoT hardware devices. Provides indexed "
        "historical lookups, per-device summaries, and time-bucketed "
        "aggregations via raw SQL optimization queries."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix: str = settings.API_PREFIX

app.include_router(general_router, prefix=prefix)
app.include_router(telemetry_router, prefix=prefix)
app.include_router(devices_router, prefix=prefix)


@app.get("/", tags=["root"])
def root() -> dict:
    """Root redirect to the interactive API docs."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api_prefix": settings.API_PREFIX,
    }
