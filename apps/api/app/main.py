"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.errors import register_exception_handlers


def create_app() -> FastAPI:
    """Create and configure the NewsFlow AI API."""

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
    )
    register_exception_handlers(application)
    application.include_router(health_router)
    return application


app = create_app()
