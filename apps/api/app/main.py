"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.core.config import DatabaseConfigurationError, Settings, get_settings
from app.core.errors import register_exception_handlers
from app.database import DatabaseConnection, DatabaseConnectionError, PostgresDatabase
from app.database.sqlalchemy import SqlAlchemyDatabase
from app.repositories import SqlAlchemyUserRepository, UserRepository
from app.security import (
    Argon2PasswordHasher,
    InMemoryRateLimiter,
    PasswordHasher,
    RateLimitExceeded,
)
from app.services import RegistrationService

logger = logging.getLogger(__name__)


def create_app(
    *,
    settings: Settings | None = None,
    database: DatabaseConnection | None = None,
    user_repository: UserRepository | None = None,
    password_hasher: PasswordHasher | None = None,
    registration_rate_limiter: InMemoryRateLimiter | None = None,
) -> FastAPI:
    """Create and configure the NewsFlow AI API."""

    application_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        configured_database = database
        database_url = None
        if configured_database is None:
            try:
                database_url = application_settings.require_database_url()
                configured_database = PostgresDatabase(
                    database_url=database_url,
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

        sqlalchemy_database = None
        configured_user_repository = user_repository
        if configured_user_repository is None:
            database_url = database_url or application_settings.require_database_url()
            sqlalchemy_database = SqlAlchemyDatabase(
                database_url=database_url,
                connect_timeout_seconds=(
                    application_settings.database_connect_timeout_seconds
                ),
            )
            configured_user_repository = SqlAlchemyUserRepository(sqlalchemy_database)

        application.state.registration_service = RegistrationService(
            users=configured_user_repository,
            password_hasher=password_hasher or Argon2PasswordHasher(),
        )
        application.state.registration_rate_limiter = (
            registration_rate_limiter
            or InMemoryRateLimiter(
                max_attempts=(application_settings.registration_rate_limit_attempts),
                window_seconds=(
                    application_settings.registration_rate_limit_window_seconds
                ),
            )
        )

        try:
            yield
        finally:
            if sqlalchemy_database is not None:
                await sqlalchemy_database.close()

    application = FastAPI(
        title="NewsFlow AI API",
        summary="Backend API for the NewsFlow AI application.",
        description=(
            "Provides health checks, secure user registration, NewsFlow AI "
            "business logic, persistence, and authorised external integrations."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    @application.middleware("http")
    async def limit_registration_attempts(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Rate limit every registration request before body validation."""

        if request.method == "POST" and request.url.path == "/api/v1/auth/register":
            limiter: InMemoryRateLimiter | None = getattr(
                request.app.state,
                "registration_rate_limiter",
                None,
            )
            if limiter is None:
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": {
                            "code": "registration_unavailable",
                            "message": "Registration is temporarily unavailable.",
                        }
                    },
                )

            client_host = request.client.host if request.client else "unknown-client"
            try:
                await limiter.check(client_host)
            except RateLimitExceeded as exc:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "registration_rate_limited",
                            "message": (
                                "Too many registration attempts. "
                                "Please try again later."
                            ),
                        }
                    },
                    headers={"Retry-After": str(exc.retry_after_seconds)},
                )

        return await call_next(request)

    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(auth_router)
    return application


app = create_app()
