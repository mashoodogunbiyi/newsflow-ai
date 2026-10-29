"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.api.routes.article_sync import router as article_sync_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.library import router as library_router
from app.core.config import DatabaseConfigurationError, Settings, get_settings
from app.core.errors import register_exception_handlers
from app.database import DatabaseConnection, DatabaseConnectionError, PostgresDatabase
from app.database.sqlalchemy import SqlAlchemyDatabase
from app.providers.factory import create_news_provider
from app.repositories import (
    AuthenticationRepository,
    SavedContentRepository,
    SqlAlchemyAuthenticationRepository,
    SqlAlchemySavedContentRepository,
    SqlAlchemyUserRepository,
    UserRepository,
)
from app.repositories.article_sync import (
    ArticleSyncRepository,
    SqlAlchemyArticleSyncRepository,
)
from app.repositories.articles import SqlAlchemyArticleRepository
from app.security import (
    Argon2PasswordHasher,
    InMemoryRateLimiter,
    PasswordHasher,
    RateLimitExceeded,
)
from app.services import AuthenticationService, RegistrationService, SavedContentService
from app.services.article_deduplication import ArticleDeduplicationService
from app.services.article_sync import ArticleSyncService

logger = logging.getLogger(__name__)


def create_app(
    *,
    settings: Settings | None = None,
    database: DatabaseConnection | None = None,
    user_repository: UserRepository | None = None,
    password_hasher: PasswordHasher | None = None,
    registration_rate_limiter: InMemoryRateLimiter | None = None,
    authentication_repository: AuthenticationRepository | None = None,
    login_rate_limiter: InMemoryRateLimiter | None = None,
    saved_content_repository: SavedContentRepository | None = None,
    article_sync_repository: ArticleSyncRepository | None = None,
    article_sync_service: ArticleSyncService | None = None,
    manual_sync_rate_limiter: InMemoryRateLimiter | None = None,
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
        configured_authentication_repository = authentication_repository
        configured_saved_content_repository = saved_content_repository
        configured_article_sync_repository = article_sync_repository
        configured_article_sync_service = article_sync_service
        if (
            configured_user_repository is None
            or configured_authentication_repository is None
            or configured_saved_content_repository is None
            or (
                application_settings.news_source_mode == "fixture"
                and (
                    configured_article_sync_repository is None
                    or configured_article_sync_service is None
                )
            )
        ):
            database_url = database_url or application_settings.require_database_url()
            sqlalchemy_database = SqlAlchemyDatabase(
                database_url=database_url,
                connect_timeout_seconds=(
                    application_settings.database_connect_timeout_seconds
                ),
            )
            if configured_user_repository is None:
                configured_user_repository = SqlAlchemyUserRepository(
                    sqlalchemy_database
                )
            if configured_authentication_repository is None:
                configured_authentication_repository = (
                    SqlAlchemyAuthenticationRepository(sqlalchemy_database)
                )
            if configured_saved_content_repository is None:
                configured_saved_content_repository = SqlAlchemySavedContentRepository(
                    sqlalchemy_database
                )
            if (
                application_settings.news_source_mode == "fixture"
                and configured_article_sync_repository is None
            ):
                configured_article_sync_repository = SqlAlchemyArticleSyncRepository(
                    sqlalchemy_database
                )
            if (
                application_settings.news_source_mode == "fixture"
                and configured_article_sync_service is None
            ):
                assert configured_article_sync_repository is not None
                configured_article_sync_service = ArticleSyncService(
                    provider=create_news_provider(application_settings),
                    source_profile_key="fixture-v1",
                    ingestion=ArticleDeduplicationService(
                        SqlAlchemyArticleRepository(sqlalchemy_database)
                    ),
                    repository=configured_article_sync_repository,
                    page_size=application_settings.article_sync_page_size,
                    max_retries=application_settings.article_sync_max_retries,
                    retry_base_seconds=(
                        application_settings.article_sync_retry_base_seconds
                    ),
                    lease_duration=timedelta(
                        seconds=application_settings.article_sync_lease_seconds
                    ),
                )

        configured_password_hasher = password_hasher or Argon2PasswordHasher()
        application.state.registration_service = RegistrationService(
            users=configured_user_repository,
            password_hasher=configured_password_hasher,
        )
        application.state.authentication_service = AuthenticationService(
            repository=configured_authentication_repository,
            password_hasher=configured_password_hasher,
            session_lifetime=timedelta(
                minutes=application_settings.session_lifetime_minutes
            ),
        )
        application.state.saved_content_service = SavedContentService(
            configured_saved_content_repository
        )
        application.state.article_sync_repository = configured_article_sync_repository
        application.state.article_sync_service = configured_article_sync_service
        application.state.registration_rate_limiter = (
            registration_rate_limiter
            or InMemoryRateLimiter(
                max_attempts=(application_settings.registration_rate_limit_attempts),
                window_seconds=(
                    application_settings.registration_rate_limit_window_seconds
                ),
            )
        )
        application.state.login_rate_limiter = (
            login_rate_limiter
            or InMemoryRateLimiter(
                max_attempts=application_settings.login_rate_limit_attempts,
                window_seconds=application_settings.login_rate_limit_window_seconds,
            )
        )
        application.state.manual_sync_rate_limiter = (
            manual_sync_rate_limiter
            or InMemoryRateLimiter(
                max_attempts=(application_settings.manual_sync_rate_limit_attempts),
                window_seconds=(
                    application_settings.manual_sync_rate_limit_window_seconds
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
            "Provides health checks, secure registration and authentication, "
            "NewsFlow AI business logic, persistence, and authorised external "
            "integrations."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[application_settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    @application.middleware("http")
    async def limit_authentication_attempts(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Rate limit credential endpoints before request-body validation."""

        limited_endpoint = {
            ("POST", "/api/v1/auth/register"): (
                "registration_rate_limiter",
                "registration_unavailable",
                "Registration is temporarily unavailable.",
                "registration_rate_limited",
                "Too many registration attempts. Please try again later.",
            ),
            ("POST", "/api/v1/auth/login"): (
                "login_rate_limiter",
                "authentication_unavailable",
                "Authentication is temporarily unavailable.",
                "login_rate_limited",
                "Too many login attempts. Please try again later.",
            ),
        }.get((request.method, request.url.path))

        if limited_endpoint is not None:
            (
                limiter_attribute,
                unavailable_code,
                unavailable_message,
                limited_code,
                limited_message,
            ) = limited_endpoint
            limiter: InMemoryRateLimiter | None = getattr(
                request.app.state, limiter_attribute, None
            )
            if limiter is None:
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": {
                            "code": unavailable_code,
                            "message": unavailable_message,
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
                            "code": limited_code,
                            "message": limited_message,
                        }
                    },
                    headers={"Retry-After": str(exc.retry_after_seconds)},
                )

        return await call_next(request)

    register_exception_handlers(application)
    application.state.session_cookie_secure = application_settings.session_cookie_secure
    application.state.session_cookie_max_age_seconds = (
        application_settings.session_lifetime_minutes * 60
    )
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(library_router)
    application.include_router(article_sync_router)
    return application


app = create_app()
