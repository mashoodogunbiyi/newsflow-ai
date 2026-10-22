"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import DatabaseConfigurationError, Settings, get_settings
from app.core.errors import register_exception_handlers
from app.database import DatabaseConnection, DatabaseConnectionError, PostgresDatabase

logger = logging.getLogger(__name__)


def create_app(
    *,
    settings: Settings | None = None,
    database: DatabaseConnection | None = None,
) -> FastAPI:
    """Create and configure the NewsFlow AI API."""

    application_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        configured_database = database
        if configured_database is None:
            try:
                configured_database = PostgresDatabase(
                    database_url=application_settings.require_database_url(),
                    connect_timeout_seconds=(
                        application_settings.database_connect_timeout_seconds
                    ),
                )
            except DatabaseConfigurationError:
                logger.error("PostgreSQL configuration is missing or invalid.")
                raise

        application.state.database = configured_database

        try:
            await configured_database.check_connection()
        except DatabaseConnectionError:
            logger.error("PostgreSQL startup connection check failed.")
            raise

        logger.info("PostgreSQL startup connection check succeeded.")
        yield

    application = FastAPI(
        title="NewsFlow AI API",
        summary="Backend API for the NewsFlow AI application.",
        description=(
            "Provides health checks and will support NewsFlow AI business logic, "
            "validation, persistence, and authorised external integrations."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    register_exception_handlers(application)
    application.include_router(health_router)
    return application


app = create_app()
