"""Consistent, safe JSON error handling for the API."""

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.logging_config import log_event

logger = logging.getLogger(__name__)


class ApplicationError(Exception):
    """An expected application failure safe to return to an API client."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = dict(headers) if headers else None
        super().__init__(message)


def _error_payload(
    *,
    code: str,
    message: str,
    details: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = list(details)
    return {"error": error}


def _response_headers(
    request: Request,
    headers: Mapping[str, str] | None = None,
) -> dict[str, str] | None:
    """Preserve safe response headers and expose the server request identifier."""

    response_headers = dict(headers) if headers else {}
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str):
        response_headers.setdefault("X-Request-ID", request_id)
    return response_headers or None


def register_exception_handlers(app: FastAPI) -> None:
    """Register the API's standard exception-to-response mappings."""

    @app.exception_handler(ApplicationError)
    async def handle_application_error(
        request: Request,
        exc: ApplicationError,
    ) -> JSONResponse:
        if exc.status_code >= 500:
            log_event(
                logger,
                logging.WARNING,
                "api_dependency_failure",
                component="backend_api",
                operation="request",
                request_id=getattr(request.state, "request_id", None),
                status="failed",
                error_category=exc.code,
                recovery_status="retry_later",
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(code=exc.code, message=exc.message),
            headers=_response_headers(request, exc.headers),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        details = [
            {
                "location": [str(part) for part in error["loc"]],
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_error_payload(
                code="validation_error",
                message="The request could not be validated.",
                details=details,
            ),
            headers=_response_headers(request),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "The request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(
                code=f"http_{exc.status_code}",
                message=message,
            ),
            headers=_response_headers(request, exc.headers),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        exception_type = type(exc).__name__
        log_event(
            logger,
            logging.ERROR,
            "api_request_failed",
            component="backend_api",
            operation=request.method.lower(),
            request_id=getattr(request.state, "request_id", None),
            status="failed",
            error_category="unexpected_error",
            error_code=exception_type,
            recovery_status="investigation_required",
        )
        return JSONResponse(
            status_code=500,
            content=_error_payload(
                code="internal_server_error",
                message="An unexpected error occurred.",
            ),
            headers=_response_headers(request),
        )
