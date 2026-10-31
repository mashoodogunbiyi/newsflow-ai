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
from app.api.routes.articles import router as articles_router
from app.api.routes.auth import router as auth_router
from app.api.routes.generation_monitoring import router as generation_monitoring_router
from app.api.routes.generations import router as generations_router
from app.api.routes.health import router as health_router
from app.api.routes.image_regeneration import router as image_regeneration_router
from app.api.routes.ingestion_observability import (
    router as ingestion_observability_router,
)
from app.api.routes.library import router as library_router
from app.api.routes.linkedin_generation import router as linkedin_generation_router
from app.core.config import DatabaseConfigurationError, Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging_config import configure_logging
from app.database import DatabaseConnection, DatabaseConnectionError, PostgresDatabase
from app.database.sqlalchemy import SqlAlchemyDatabase
from app.models.image_safety import ImageProviderSafetyCapabilities
from app.providers.factory import create_news_provider
from app.repositories import (
    AuthenticationRepository,
    SavedContentRepository,
    SqlAlchemyAuthenticationRepository,
    SqlAlchemySavedContentRepository,
    SqlAlchemyUserRepository,
    UserRepository,
)
from app.repositories.article_catalogue import (
    ArticleCatalogueRepository,
    SqlAlchemyArticleCatalogueRepository,
)
from app.repositories.article_rights import (
    ArticleRightsRepository,
    SqlAlchemyArticleRightsRepository,
)
from app.repositories.article_sync import (
    ArticleSyncRepository,
    SqlAlchemyArticleSyncRepository,
)
from app.repositories.articles import SqlAlchemyArticleRepository
from app.repositories.generated_images import SqlAlchemyGeneratedImageRepository
from app.repositories.generation_audit import SqlAlchemyGenerationAuditRepository
from app.repositories.generation_usage import SqlAlchemyGenerationUsageRepository
from app.repositories.image_regeneration import (
    SqlAlchemyImageRegenerationRepository,
)
from app.repositories.linkedin_generation import (
    LinkedInGenerationRepository,
    SqlAlchemyLinkedInGenerationRepository,
)
from app.security import (
    Argon2PasswordHasher,
    InMemoryRateLimiter,
    PasswordHasher,
    RateLimitExceeded,
)
from app.services import AuthenticationService, RegistrationService, SavedContentService
from app.services.article_catalogue import ArticleCatalogueService
from app.services.article_deduplication import ArticleDeduplicationService
from app.services.article_rights import ArticleRightsService
from app.services.article_sync import ArticleSyncService
from app.services.generated_image_storage import GeneratedImageStorageService
from app.services.generation_audit import GenerationAuditService
from app.services.generation_monitoring import GenerationMonitoringService
from app.services.generation_usage import GenerationUsageService
from app.services.image_prompt import ImagePromptComposer
from app.services.image_regeneration import (
    ImageGeneratorFactory,
    ImageRegenerationService,
)
from app.services.image_safety import ImageSafetyService
from app.services.image_storage import LocalPrivateImageStorage
from app.services.image_validation import GeneratedImageValidationService
from app.services.ingestion_observability import IngestionObservabilityService
from app.services.linkedin_generation import (
    AITextGeneratorFactory,
    LinkedInGenerationService,
)
from app.services.openai_image_service import OpenAIImageGenerationService
from app.services.openai_service import OpenAIService

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
    article_catalogue_repository: ArticleCatalogueRepository | None = None,
    article_catalogue_service: ArticleCatalogueService | None = None,
    article_sync_repository: ArticleSyncRepository | None = None,
    article_sync_service: ArticleSyncService | None = None,
    manual_sync_rate_limiter: InMemoryRateLimiter | None = None,
    ingestion_observability_service: IngestionObservabilityService | None = None,
    article_rights_repository: ArticleRightsRepository | None = None,
    linkedin_generation_repository: LinkedInGenerationRepository | None = None,
    linkedin_generation_service: LinkedInGenerationService | None = None,
    generation_usage_service: GenerationUsageService | None = None,
    generation_audit_service: GenerationAuditService | None = None,
    generation_monitoring_service: GenerationMonitoringService | None = None,
    image_regeneration_service: ImageRegenerationService | None = None,
    openai_factory: AITextGeneratorFactory | None = None,
    image_generator_factory: ImageGeneratorFactory | None = None,
    generation_rate_limiter: InMemoryRateLimiter | None = None,
) -> FastAPI:
    """Create and configure the NewsFlow AI API."""

    application_settings = settings or get_settings()
    configure_logging(
        level=application_settings.log_level,
        log_format=application_settings.log_format,
    )

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
        configured_article_catalogue_repository = article_catalogue_repository
        configured_article_catalogue_service = article_catalogue_service
        configured_article_sync_repository = article_sync_repository
        configured_article_sync_service = article_sync_service
        configured_ingestion_observability_service = ingestion_observability_service
        configured_article_rights_repository = article_rights_repository
        configured_linkedin_generation_repository = linkedin_generation_repository
        configured_linkedin_generation_service = linkedin_generation_service
        configured_generation_usage_service = generation_usage_service
        configured_generation_audit_service = generation_audit_service
        configured_generation_monitoring_service = generation_monitoring_service
        configured_image_regeneration_service = image_regeneration_service
        if (
            configured_user_repository is None
            or configured_authentication_repository is None
            or configured_saved_content_repository is None
            or configured_article_catalogue_service is None
            or configured_linkedin_generation_service is None
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
            if configured_article_catalogue_repository is None:
                configured_article_catalogue_repository = (
                    SqlAlchemyArticleCatalogueRepository(sqlalchemy_database)
                )
            if configured_article_catalogue_service is None:
                configured_article_catalogue_service = ArticleCatalogueService(
                    configured_article_catalogue_repository
                )
            if configured_article_rights_repository is None:
                configured_article_rights_repository = (
                    SqlAlchemyArticleRightsRepository(sqlalchemy_database)
                )
            if configured_linkedin_generation_repository is None:
                configured_linkedin_generation_repository = (
                    SqlAlchemyLinkedInGenerationRepository(sqlalchemy_database)
                )
            if configured_generation_usage_service is None:
                configured_generation_usage_service = GenerationUsageService(
                    repository=SqlAlchemyGenerationUsageRepository(sqlalchemy_database),
                    daily_limit=application_settings.generation_daily_limit,
                    concurrent_limit=(application_settings.generation_concurrent_limit),
                    attempt_timeout=timedelta(
                        seconds=(
                            application_settings.generation_attempt_timeout_seconds
                        )
                    ),
                    retention=timedelta(
                        days=application_settings.generation_usage_retention_days
                    ),
                )
            generation_audit_repository = SqlAlchemyGenerationAuditRepository(
                sqlalchemy_database
            )
            if configured_generation_audit_service is None:
                configured_generation_audit_service = GenerationAuditService(
                    repository=generation_audit_repository,
                    retention=timedelta(
                        days=application_settings.generation_audit_retention_days
                    ),
                )
            if configured_generation_monitoring_service is None:
                configured_generation_monitoring_service = GenerationMonitoringService(
                    repository=generation_audit_repository,
                    default_window_hours=(
                        application_settings.generation_monitoring_window_hours
                    ),
                )
            if configured_linkedin_generation_service is None:
                assert configured_article_rights_repository is not None
                assert configured_linkedin_generation_repository is not None
                configured_linkedin_generation_service = LinkedInGenerationService(
                    repository=configured_linkedin_generation_repository,
                    rights=ArticleRightsService(configured_article_rights_repository),
                    openai_factory=(
                        openai_factory
                        or (lambda: OpenAIService.from_settings(application_settings))
                    ),
                    usage=configured_generation_usage_service,
                    audit=configured_generation_audit_service,
                )
            if (
                configured_image_regeneration_service is None
                and application_settings.app_env in {"development", "test"}
            ):
                assert configured_article_rights_repository is not None
                assert configured_linkedin_generation_repository is not None
                image_storage_configuration = (
                    application_settings.require_image_storage_configuration()
                )
                generated_image_repository = SqlAlchemyGeneratedImageRepository(
                    sqlalchemy_database
                )
                configured_image_regeneration_service = ImageRegenerationService(
                    images=generated_image_repository,
                    runs=SqlAlchemyImageRegenerationRepository(sqlalchemy_database),
                    drafts=configured_linkedin_generation_repository,
                    rights=ArticleRightsService(configured_article_rights_repository),
                    prompt_composer=ImagePromptComposer(),
                    safety=ImageSafetyService(
                        provider_capabilities=ImageProviderSafetyCapabilities(
                            prompt_moderation_available=True,
                            output_moderation_available=True,
                            strict_safety_level_available=False,
                            content_credentials_available=False,
                        )
                    ),
                    image_generator_factory=(
                        image_generator_factory
                        or (
                            lambda: OpenAIImageGenerationService.from_settings(
                                application_settings
                            )
                        )
                    ),
                    storage=GeneratedImageStorageService(
                        validator=GeneratedImageValidationService(
                            image_storage_configuration
                        ),
                        storage=LocalPrivateImageStorage(
                            image_storage_configuration.local_root
                        ),
                        repository=generated_image_repository,
                    ),
                    usage=configured_generation_usage_service,
                )
            if configured_article_sync_repository is None:
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
        if (
            configured_ingestion_observability_service is None
            and configured_article_sync_repository is not None
        ):
            configured_ingestion_observability_service = IngestionObservabilityService(
                repository=configured_article_sync_repository,
                metrics_enabled=(application_settings.ingestion_metrics_enabled),
                metrics_window_hours=(
                    application_settings.ingestion_metrics_window_hours
                ),
                failure_threshold=(application_settings.ingestion_failure_threshold),
                success_stale_seconds=(
                    application_settings.ingestion_success_stale_seconds
                ),
                long_running_seconds=(
                    application_settings.ingestion_long_running_seconds
                ),
                rejection_rate_percent=(
                    application_settings.ingestion_rejection_rate_percent
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
        application.state.article_catalogue_service = (
            configured_article_catalogue_service
        )
        application.state.article_sync_repository = configured_article_sync_repository
        application.state.article_sync_service = configured_article_sync_service
        application.state.ingestion_observability_service = (
            configured_ingestion_observability_service
        )
        application.state.linkedin_generation_service = (
            configured_linkedin_generation_service
        )
        application.state.generation_audit_service = configured_generation_audit_service
        application.state.generation_monitoring_service = (
            configured_generation_monitoring_service
        )
        application.state.image_regeneration_service = (
            configured_image_regeneration_service
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
        application.state.generation_rate_limiter = (
            generation_rate_limiter
            or InMemoryRateLimiter(
                max_attempts=application_settings.generation_rate_limit_attempts,
                window_seconds=(
                    application_settings.generation_rate_limit_window_seconds
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
        allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key"],
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
    application.include_router(generations_router)
    application.include_router(generation_monitoring_router)
    application.include_router(library_router)
    application.include_router(articles_router)
    application.include_router(article_sync_router)
    application.include_router(ingestion_observability_router)
    application.include_router(linkedin_generation_router)
    application.include_router(image_regeneration_router)
    return application


app = create_app()
