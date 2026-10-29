"""NFA-38 secure OpenAI integration service tests with no live requests."""

import asyncio
import logging
from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest
from pydantic import SecretStr, ValidationError

from app.core.ai_config import OpenAIServiceConfiguration
from app.core.config import OpenAIConfigurationError, Settings
from app.models.ai import AITextGenerationRequest
from app.services.openai_service import (
    OpenAIAuthenticationFailure,
    OpenAIInvalidResponseError,
    OpenAIOutputLimitError,
    OpenAIRateLimitFailure,
    OpenAIService,
    OpenAITimeoutFailure,
    OpenAIUnavailableFailure,
)

MODEL = "test-openai-model"
API_KEY = "test-openai-api-key-not-a-real-credential"
SENSITIVE_PROMPT = "private permitted test input that must not be logged"
PROVIDER_DETAIL = "provider failure detail that must not be logged"


def run(coroutine):
    return asyncio.run(coroutine)


class FakeResponses:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


class FakeClient:
    def __init__(self, outcome: object) -> None:
        self.responses = FakeResponses(outcome)
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def configuration(**overrides: object) -> OpenAIServiceConfiguration:
    values: dict[str, object] = {
        "api_key": SecretStr(API_KEY),
        "model": MODEL,
        "request_timeout": 30,
        "max_output_tokens": 800,
        "max_retries": 2,
    }
    values.update(overrides)
    return OpenAIServiceConfiguration.model_validate(values)


def successful_response(
    *,
    output_text: str = "A professional synthetic LinkedIn draft.",
    usage: object | None = None,
    status: str = "completed",
) -> object:
    return SimpleNamespace(
        id="resp_test_123",
        _request_id="req_test_123",
        model=MODEL,
        status=status,
        output_text=output_text,
        usage=usage,
    )


def status_error(error_type: type[openai.APIStatusError], status_code: int):
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(
        status_code,
        request=request,
        headers={"x-request-id": "req_failure_123"},
    )
    return error_type(
        PROVIDER_DETAIL + " containing " + API_KEY,
        response=response,
        body={"error": {"message": "provider failure"}},
    )


def test_successful_generation_returns_structured_result_and_usage() -> None:
    usage = SimpleNamespace(input_tokens=120, output_tokens=45, total_tokens=165)
    client = FakeClient(successful_response(usage=usage))
    service = OpenAIService(configuration=configuration(), client=client)
    request = AITextGenerationRequest(
        input_text=SENSITIVE_PROMPT,
        instructions="Write a factual professional draft.",
        max_output_tokens=400,
    )

    result = run(service.generate_text(request))

    assert result.text == "A professional synthetic LinkedIn draft."
    assert result.model == MODEL
    assert result.response_id == "resp_test_123"
    assert result.request_id == "req_test_123"
    assert result.usage.input_tokens == 120
    assert result.usage.output_tokens == 45
    assert result.usage.total_tokens == 165
    assert client.responses.calls == [
        {
            "model": MODEL,
            "input": SENSITIVE_PROMPT,
            "max_output_tokens": 400,
            "store": False,
            "instructions": "Write a factual professional draft.",
        }
    ]


def test_sdk_client_receives_secret_timeout_and_bounded_retry_configuration() -> None:
    client = FakeClient(successful_response())
    received: dict[str, object] = {}

    def client_factory(**kwargs: object) -> FakeClient:
        received.update(kwargs)
        return client

    service = OpenAIService.from_settings(
        Settings(
            _env_file=None,
            openai_api_key=API_KEY,
            openai_model=MODEL,
            openai_request_timeout=12,
            openai_max_output_tokens=500,
            openai_max_retries=1,
        ),
        client_factory=client_factory,
    )

    result = run(
        service.generate_text(
            AITextGenerationRequest(input_text="Synthetic authorised input.")
        )
    )
    run(service.close())

    assert result.text
    assert received == {
        "api_key": API_KEY,
        "timeout": 12,
        "max_retries": 1,
    }
    assert client.responses.calls[0]["max_output_tokens"] == 500
    assert client.closed is True


def test_missing_api_key_fails_before_client_initialisation() -> None:
    called = False

    def client_factory(**kwargs: object) -> FakeClient:
        nonlocal called
        called = True
        raise AssertionError(kwargs)

    with pytest.raises(OpenAIConfigurationError, match="OPENAI_API_KEY must be set"):
        OpenAIService.from_settings(
            Settings(_env_file=None, openai_api_key=None, openai_model=MODEL),
            client_factory=client_factory,
        )

    assert called is False


def test_output_limit_is_enforced_before_provider_access() -> None:
    client = FakeClient(successful_response())
    service = OpenAIService(
        configuration=configuration(max_output_tokens=300),
        client=client,
    )

    with pytest.raises(OpenAIOutputLimitError) as error:
        run(
            service.generate_text(
                AITextGenerationRequest(
                    input_text="Synthetic authorised input.",
                    max_output_tokens=301,
                )
            )
        )

    assert error.value.code == "openai_output_limit_exceeded"
    assert error.value.retryable is False
    assert client.responses.calls == []


def test_authentication_failure_is_safe_and_not_retryable() -> None:
    client = FakeClient(status_error(openai.AuthenticationError, 401))
    service = OpenAIService(configuration=configuration(), client=client)

    with pytest.raises(OpenAIAuthenticationFailure) as error:
        run(service.generate_text(AITextGenerationRequest(input_text=SENSITIVE_PROMPT)))

    assert error.value.code == "openai_authentication_failed"
    assert error.value.retryable is False
    assert error.value.request_id == "req_failure_123"
    assert API_KEY not in str(error.value)
    assert SENSITIVE_PROMPT not in str(error.value)


def test_rate_limit_failure_is_retryable_after_sdk_budget() -> None:
    client = FakeClient(status_error(openai.RateLimitError, 429))
    service = OpenAIService(configuration=configuration(max_retries=2), client=client)

    with pytest.raises(OpenAIRateLimitFailure) as error:
        run(
            service.generate_text(
                AITextGenerationRequest(input_text="Synthetic authorised input.")
            )
        )

    assert error.value.code == "openai_rate_limited"
    assert error.value.retryable is True
    assert error.value.request_id == "req_failure_123"


def test_timeout_failure_is_controlled_and_retryable() -> None:
    provider_error = openai.APITimeoutError(
        httpx.Request("POST", "https://api.openai.com/v1/responses")
    )
    client = FakeClient(provider_error)
    service = OpenAIService(configuration=configuration(), client=client)

    with pytest.raises(OpenAITimeoutFailure) as error:
        run(
            service.generate_text(
                AITextGenerationRequest(input_text="Synthetic authorised input.")
            )
        )

    assert error.value.code == "openai_timeout"
    assert error.value.retryable is True


def test_connection_failure_is_mapped_to_temporary_unavailability() -> None:
    provider_error = openai.APIConnectionError(
        message="connection failed with " + API_KEY,
        request=httpx.Request("POST", "https://api.openai.com/v1/responses"),
    )
    client = FakeClient(provider_error)
    service = OpenAIService(configuration=configuration(), client=client)

    with pytest.raises(OpenAIUnavailableFailure) as error:
        run(
            service.generate_text(
                AITextGenerationRequest(input_text="Synthetic authorised input.")
            )
        )

    assert error.value.code == "openai_unavailable"
    assert error.value.retryable is True
    assert API_KEY not in str(error.value)


@pytest.mark.parametrize(
    ("status", "output_text", "expected_code"),
    [
        ("incomplete", "Partial text", "openai_incomplete_response"),
        ("completed", "   ", "openai_empty_response"),
    ],
)
def test_incomplete_or_empty_responses_fail_safely(
    status: str,
    output_text: str,
    expected_code: str,
) -> None:
    client = FakeClient(successful_response(status=status, output_text=output_text))
    service = OpenAIService(configuration=configuration(), client=client)

    with pytest.raises(OpenAIInvalidResponseError) as error:
        run(
            service.generate_text(
                AITextGenerationRequest(input_text="Synthetic authorised input.")
            )
        )

    assert error.value.code == expected_code


def test_usage_is_optional_when_provider_does_not_return_it() -> None:
    client = FakeClient(successful_response(usage=None))
    service = OpenAIService(configuration=configuration(), client=client)

    result = run(
        service.generate_text(
            AITextGenerationRequest(input_text="Synthetic authorised input.")
        )
    )

    assert result.usage.input_tokens is None
    assert result.usage.output_tokens is None
    assert result.usage.total_tokens is None


def test_sensitive_prompt_key_and_provider_message_are_not_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = FakeClient(status_error(openai.AuthenticationError, 401))
    service = OpenAIService(configuration=configuration(), client=client)

    with caplog.at_level(logging.INFO, logger="app.services.openai_service"):
        with pytest.raises(OpenAIAuthenticationFailure):
            run(
                service.generate_text(
                    AITextGenerationRequest(input_text=SENSITIVE_PROMPT)
                )
            )

    assert "openai_generation_failed" in caplog.text
    assert caplog.records[-1].error_code == "openai_authentication_failed"
    assert SENSITIVE_PROMPT not in caplog.text
    assert API_KEY not in caplog.text
    assert PROVIDER_DETAIL not in caplog.text


def test_sensitive_request_representation_is_masked_and_rejects_blank_text() -> None:
    request = AITextGenerationRequest(
        input_text=SENSITIVE_PROMPT,
        instructions="Sensitive instructions.",
    )

    assert SENSITIVE_PROMPT not in repr(request)
    assert "Sensitive instructions." not in repr(request)
    assert "**********" in repr(request)
    with pytest.raises(ValidationError):
        AITextGenerationRequest(input_text="   ")
