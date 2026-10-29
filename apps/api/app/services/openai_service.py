"""Secure reusable OpenAI Responses API integration for backend workflows."""

import logging
from collections.abc import Callable
from typing import Any, Protocol

import openai
from openai import AsyncOpenAI

from app.core.ai_config import OpenAIServiceConfiguration
from app.core.config import Settings, get_settings
from app.core.logging_config import log_event
from app.models.ai import (
    AITextGenerationRequest,
    AITextGenerationResult,
    AITokenUsage,
)

logger = logging.getLogger(__name__)


class AsyncResponsesResource(Protocol):
    """Small SDK boundary required by the service and mocked by unit tests."""

    async def create(self, **kwargs: Any) -> Any: ...


class AsyncOpenAIClient(Protocol):
    """Structural type for the official client and isolated test doubles."""

    responses: AsyncResponsesResource

    async def close(self) -> None: ...


OpenAIClientFactory = Callable[..., AsyncOpenAIClient]


class OpenAIServiceError(RuntimeError):
    """Safe application-level failure returned by the OpenAI boundary."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        retryable: bool,
        request_id: str | None = None,
    ) -> None:
        self.code = code
        self.safe_message = message
        self.retryable = retryable
        self.request_id = request_id
        super().__init__(message)


class OpenAIAuthenticationFailure(OpenAIServiceError):
    """Raised for a permanent credential rejection."""


class OpenAIRateLimitFailure(OpenAIServiceError):
    """Raised after the configured SDK retry budget is exhausted."""


class OpenAITimeoutFailure(OpenAIServiceError):
    """Raised after the configured request deadline and retries are exhausted."""


class OpenAIUnavailableFailure(OpenAIServiceError):
    """Raised for a temporary connection or provider availability failure."""


class OpenAIRequestFailure(OpenAIServiceError):
    """Raised for another non-retryable provider rejection."""


class OpenAIInvalidResponseError(OpenAIServiceError):
    """Raised when the provider response is incomplete or has no usable text."""


class OpenAIOutputLimitError(OpenAIServiceError):
    """Raised before access when a request exceeds the configured cost limit."""


class OpenAIService:
    """Generate text through one bounded, backend-only OpenAI client."""

    def __init__(
        self,
        *,
        configuration: OpenAIServiceConfiguration,
        client: AsyncOpenAIClient,
    ) -> None:
        self._configuration = configuration
        self._client = client

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        *,
        client_factory: OpenAIClientFactory = AsyncOpenAI,
    ) -> "OpenAIService":
        """Validate configuration and initialise the official asynchronous SDK."""

        configuration = (settings or get_settings()).require_openai_configuration()
        client = client_factory(
            api_key=configuration.api_key.get_secret_value(),
            timeout=configuration.request_timeout,
            max_retries=configuration.max_retries,
        )
        return cls(configuration=configuration, client=client)

    async def generate_text(
        self,
        request: AITextGenerationRequest,
    ) -> AITextGenerationResult:
        """Return generated text and usage without logging prompt or output content."""

        output_limit = request.max_output_tokens or (
            self._configuration.max_output_tokens
        )
        if output_limit > self._configuration.max_output_tokens:
            error = OpenAIOutputLimitError(
                code="openai_output_limit_exceeded",
                message="The requested AI output limit exceeds the allowed maximum.",
                retryable=False,
            )
            self._log_failure(error)
            raise error

        arguments: dict[str, Any] = {
            "model": self._configuration.model,
            "input": request.input_text.get_secret_value(),
            "max_output_tokens": output_limit,
            "store": False,
        }
        if request.instructions is not None:
            arguments["instructions"] = request.instructions.get_secret_value()
        if request.json_schema_format is not None:
            arguments["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": request.json_schema_format.name,
                    "strict": True,
                    "schema": request.json_schema_format.schema_definition,
                }
            }

        try:
            response = await self._client.responses.create(**arguments)
        except openai.AuthenticationError as exc:
            error = OpenAIAuthenticationFailure(
                code="openai_authentication_failed",
                message="AI service authentication failed.",
                retryable=False,
                request_id=self._request_id(exc),
            )
            self._log_failure(error)
            raise error from exc
        except openai.RateLimitError as exc:
            error = OpenAIRateLimitFailure(
                code="openai_rate_limited",
                message="The AI service is temporarily rate limited.",
                retryable=True,
                request_id=self._request_id(exc),
            )
            self._log_failure(error)
            raise error from exc
        except openai.APITimeoutError as exc:
            error = OpenAITimeoutFailure(
                code="openai_timeout",
                message="The AI service request timed out.",
                retryable=True,
                request_id=self._request_id(exc),
            )
            self._log_failure(error)
            raise error from exc
        except (openai.APIConnectionError, openai.InternalServerError) as exc:
            error = OpenAIUnavailableFailure(
                code="openai_unavailable",
                message="The AI service is temporarily unavailable.",
                retryable=True,
                request_id=self._request_id(exc),
            )
            self._log_failure(error)
            raise error from exc
        except openai.APIStatusError as exc:
            error = OpenAIRequestFailure(
                code="openai_request_rejected",
                message="The AI service rejected the generation request.",
                retryable=False,
                request_id=self._request_id(exc),
            )
            self._log_failure(error)
            raise error from exc
        except openai.APIError as exc:
            error = OpenAIUnavailableFailure(
                code="openai_unavailable",
                message="The AI service request could not be completed.",
                retryable=True,
                request_id=self._request_id(exc),
            )
            self._log_failure(error)
            raise error from exc

        response_request_id = getattr(response, "_request_id", None)
        response_status = getattr(response, "status", None)
        output_text = getattr(response, "output_text", None)
        if response_status != "completed" or not isinstance(output_text, str):
            error = OpenAIInvalidResponseError(
                code="openai_incomplete_response",
                message="The AI service returned an incomplete response.",
                retryable=False,
                request_id=response_request_id,
            )
            self._log_failure(error)
            raise error
        output_text = output_text.strip()
        if not output_text:
            error = OpenAIInvalidResponseError(
                code="openai_empty_response",
                message="The AI service returned no usable text.",
                retryable=False,
                request_id=response_request_id,
            )
            self._log_failure(error)
            raise error

        usage = self._usage(getattr(response, "usage", None))
        result = AITextGenerationResult(
            text=output_text,
            model=(getattr(response, "model", None) or self._configuration.model),
            response_id=getattr(response, "id", None),
            request_id=response_request_id,
            usage=usage,
        )
        log_event(
            logger,
            logging.INFO,
            "openai_generation_completed",
            model=result.model,
            request_id=result.request_id,
            status="completed",
            counts=usage.model_dump(exclude_none=True),
        )
        return result

    async def close(self) -> None:
        """Release connections owned by the asynchronous SDK client."""

        await self._client.close()

    def _log_failure(self, error: OpenAIServiceError) -> None:
        log_event(
            logger,
            logging.WARNING,
            "openai_generation_failed",
            model=self._configuration.model,
            request_id=error.request_id,
            status="failed",
            error_code=error.code,
        )

    @staticmethod
    def _request_id(error: BaseException) -> str | None:
        request_id = getattr(error, "request_id", None)
        return request_id if isinstance(request_id, str) else None

    @staticmethod
    def _usage(provider_usage: Any) -> AITokenUsage:
        if provider_usage is None:
            return AITokenUsage()
        return AITokenUsage(
            input_tokens=getattr(provider_usage, "input_tokens", None),
            output_tokens=getattr(provider_usage, "output_tokens", None),
            total_tokens=getattr(provider_usage, "total_tokens", None),
        )
