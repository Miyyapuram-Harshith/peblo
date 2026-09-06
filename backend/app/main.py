from __future__ import annotations

"""Peblo TV Mini - FastAPI Application."""
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import artwork, auth, catalogue, episodes, health, seasons, shows
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.session import async_session_factory, engine
from app.models import Base
from app.services.seeder import run_seed

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    settings = get_settings()
    setup_logging("DEBUG" if settings.debug else "INFO")

    logger.info("app.startup", env=settings.app_env)

    # Create tables (for dev/Docker; production uses Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed data
    if settings.seed_on_startup:
        async with async_session_factory() as session:
            await run_seed(session)

    # Ensure storage directory exists
    storage_path = Path(settings.storage_local_path)
    storage_path.mkdir(parents=True, exist_ok=True)

    yield

    # Shutdown
    await engine.dispose()
    logger.info("app.shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Peblo TV Mini API",
        description="Content Operations & Publishing Platform",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Request ID middleware
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Routes
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(shows.router, prefix="/api/v1")
    app.include_router(seasons.router, prefix="/api/v1")
    app.include_router(episodes.router, prefix="/api/v1")
    app.include_router(artwork.router, prefix="/api/v1")
    app.include_router(catalogue.validation_router, prefix="/api/v1")
    app.include_router(catalogue.admin_router, prefix="/api/v1")
    app.include_router(catalogue.viewer_router, prefix="/api/v1")

    # Serve storage files
    storage_path = Path(settings.storage_local_path)
    storage_path.mkdir(parents=True, exist_ok=True)
    app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")

    return app


app = create_app()
