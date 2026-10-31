"""NFA-50 OpenAI image service tests with no live provider requests."""

import asyncio
import base64
import logging
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import httpx
import openai
import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import OpenAIConfigurationError, Settings
from app.core.image_generation_config import OpenAIImageGenerationConfiguration
from app.models.article_rights import (
    ArticleRightsDecision,
    ArticleUseOperation,
    RightsDecisionReason,
)
from app.models.image_generation import (
    ImageDataReferenceKind,
    ImageGenerationQuality,
    ImageGenerationSize,
    ImageOutputFormat,
    OpenAIImageGenerationRequest,
)
from app.models.image_prompt import (
    IllustrationStyle,
    ImageAspectRatio,
    ImageComposition,
    ImagePromptContextKind,
    ImagePromptRequest,
    ImagePromptResult,
    ImagePromptSourceReference,
)
from app.models.image_safety import (
    ImageProviderSafetyControls,
    ImageSafetyDecision,
    ImageSafetyReasonCode,
    ImageSafetyResult,
    RequiredImageTreatment,
    SensitiveNewsCategory,
)
from app.services.openai_image_service import (
    DuplicateImageGenerationError,
    ImageGenerationRightsDeniedError,
    ImageGenerationSafetyDeniedError,
    OpenAIImageAuthenticationError,
    OpenAIImageGenerationService,
    OpenAIImageInvalidResponseError,
    OpenAIImageModerationError,
    OpenAIImageQuotaError,
    OpenAIImageRateLimitError,
    OpenAIImageTimeoutError,
    OpenAIImageUnavailableError,
)

API_KEY = "test-openai-image-key-not-a-real-credential"
MODEL = "gpt-image-2.5-flare"
ARTICLE_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
RIGHTS_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
GENERATION_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
EVALUATION_ID = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
REQUEST_ID = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
PNG_BYTES = b"\x89PNG\r\n\x1a\nsynthetic-image-content"
PRIVATE_PROMPT_TEXT = "Synthetic private technology context for provider tests"
PROVIDER_DETAIL = "private provider detail containing " + API_KEY


def run(coroutine):
    return asyncio.run(coroutine)


class FakeImages:
    def __init__(self, *outcomes: object) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    async def generate(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, *outcomes: object) -> None:
        self.images = FakeImages(*outcomes)
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class RecordingAdapter:
    def __init__(self) -> None:
        self.records: list[object] = []

    async def record_generation(self, record: object) -> None:
        self.records.append(record)


def configuration(**overrides: object) -> OpenAIImageGenerationConfiguration:
    values: dict[str, object] = {
        "api_key": SecretStr(API_KEY),
        "model": MODEL,
        "request_timeout_seconds": 30,
        "max_concurrent_requests": 2,
        "max_retries": 1,
        "retry_base_seconds": 0,
        "max_response_bytes": 1_048_576,
        "duplicate_cache_size": 10,
    }
    values.update(overrides)
    return OpenAIImageGenerationConfiguration.model_validate(values)


def approved_prompt() -> ImagePromptResult:
    preferences = ImagePromptRequest(
        article_id=ARTICLE_ID,
        generation_id=GENERATION_ID,
        style=IllustrationStyle.ABSTRACT_TECHNOLOGY,
        aspect_ratio=ImageAspectRatio.SQUARE,
        composition=ImageComposition.BALANCED,
    )
    return ImagePromptResult(
        prompt_version="image_prompt_v1",
        context_kind=ImagePromptContextKind.LINKEDIN_DRAFT,
        generation_id=GENERATION_ID,
        preferences=preferences,
        included_source_fields=("title", "description", "permitted_content"),
        included_derived_fields=("linkedin_draft",),
        source_reference=ImagePromptSourceReference(
            article_id=ARTICLE_ID,
            title="Synthetic technology topic",
            source_name="Synthetic News Provider",
            canonical_url="https://news.example.invalid/articles/synthetic-tech",
            attribution_text="Synthetic provider attribution",
            rights_version_id=RIGHTS_ID,
        ),
        trusted_instructions=SecretStr(
            "Create an original conceptual editorial illustration."
        ),
        untrusted_context=SecretStr(
            "UNTRUSTED_IMAGE_CONTEXT_JSON\n"
            '{"article":{"title":"' + PRIVATE_PROMPT_TEXT + '"}}\n'
            "END_UNTRUSTED_IMAGE_CONTEXT_JSON"
        ),
    )


def safety_result(
    decision: ImageSafetyDecision = ImageSafetyDecision.ALLOWED,
) -> ImageSafetyResult:
    allowed = decision in {
        ImageSafetyDecision.ALLOWED,
        ImageSafetyDecision.ALLOWED_WITH_RESTRICTIONS,
    }
    return ImageSafetyResult(
        evaluation_id=EVALUATION_ID,
        policy_version="image_safety_v1",
        article_id=ARTICLE_ID,
        generation_id=GENERATION_ID,
        decision=decision,
        reason_code=(
            ImageSafetyReasonCode.ORDINARY_CONCEPTUAL_TOPIC
            if allowed
            else ImageSafetyReasonCode.SAFETY_OVERRIDE_ATTEMPT
        ),
        reason_message="Content-free test policy decision.",
        sensitive_categories=(SensitiveNewsCategory.NON_SENSITIVE,),
        provider_call_allowed=allowed,
        required_treatment=RequiredImageTreatment.CONCEPTUAL_ILLUSTRATION,
        conceptual_alternative_available=allowed,
        provider_controls=ImageProviderSafetyControls(
            prompt_moderation_enabled=True,
            output_moderation_enabled=True,
            strict_safety_level_enabled=False,
            content_credentials_requested=True,
        ),
        evaluated_at=datetime(2026, 10, 30, 12, 0, tzinfo=UTC),
    )


def rights_decision(*, allowed: bool = True) -> ArticleRightsDecision:
    return ArticleRightsDecision(
        article_id=ARTICLE_ID,
        operation=ArticleUseOperation.USE_FOR_AI_GENERATION,
        allowed=allowed,
        reason=(
            RightsDecisionReason.PERMITTED
            if allowed
            else RightsDecisionReason.OPERATION_RESTRICTED
        ),
        rights_version_id=RIGHTS_ID,
        attribution_required=True,
        attribution_text="Synthetic provider attribution",
    )


def generation_request(**overrides: object) -> OpenAIImageGenerationRequest:
    values: dict[str, object] = {
        "request_id": REQUEST_ID,
        "prompt": approved_prompt(),
        "safety_result": safety_result(),
        "rights_decision": rights_decision(),
        "quality": ImageGenerationQuality.MEDIUM,
        "output_format": ImageOutputFormat.PNG,
        "safety_identifier": SecretStr("nf_" + "a" * 64),
    }
    values.update(overrides)
    return OpenAIImageGenerationRequest.model_validate(values)


def successful_response(
    *,
    image_bytes: bytes = PNG_BYTES,
    usage: object | None = None,
    url: str | None = None,
) -> object:
    item = SimpleNamespace(
        b64_json=(base64.b64encode(image_bytes).decode() if url is None else None),
        url=url,
        revised_prompt="Provider text that must not be stored or logged.",
    )
    return SimpleNamespace(
        data=[item],
        _request_id="req_image_success_123",
        model=MODEL,
        created=1_798_800_000,
        usage=usage,
    )


def status_error(
    error_type: type[openai.APIStatusError],
    status_code: int,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, object] | None = None,
):
    request = httpx.Request("POST", "https://api.openai.com/v1/images/generations")
    response = httpx.Response(
        status_code,
        request=request,
        headers={"x-request-id": "req_image_failure_123", **(headers or {})},
    )
    return error_type(
        PROVIDER_DETAIL,
        response=response,
        body=body or {"error": {"message": PROVIDER_DETAIL}},
    )


def test_successful_generation_returns_masked_data_usage_and_safe_record() -> None:
    usage = SimpleNamespace(
        input_tokens=100,
        output_tokens=200,
        total_tokens=300,
        input_tokens_details=SimpleNamespace(text_tokens=100, image_tokens=0),
        output_tokens_details=SimpleNamespace(image_tokens=200),
    )
    client = FakeClient(successful_response(usage=usage))
    recorder = RecordingAdapter()
    service = OpenAIImageGenerationService(
        configuration=configuration(),
        client=client,
        recorder=recorder,
    )

    result = run(service.generate(generation_request()))

    assert result.provider == "openai"
    assert result.model_identifier == MODEL
    assert result.provider_request_id == "req_image_success_123"
    assert result.image_data_reference.kind == ImageDataReferenceKind.INLINE_BYTES
    assert result.image_data_reference.data is not None
    assert result.image_data_reference.data.get_secret_value() == PNG_BYTES
    assert result.image_data_reference.byte_length == len(PNG_BYTES)
    assert result.usage_metadata.total_tokens == 300
    assert result.usage_metadata.input_text_tokens == 100
    assert result.usage_metadata.output_image_tokens == 200
    assert result.human_review_required is True
    assert len(recorder.records) == 1
    record_text = repr(recorder.records[0])
    assert base64.b64encode(PNG_BYTES).decode() not in record_text
    assert PRIVATE_PROMPT_TEXT not in record_text


def test_provider_receives_only_controlled_image_arguments() -> None:
    client = FakeClient(successful_response())
    service = OpenAIImageGenerationService(
        configuration=configuration(),
        client=client,
    )

    run(service.generate(generation_request()))

    call = client.images.calls[0]
    assert call["model"] == MODEL
    assert call["n"] == 1
    assert call["size"] == "1024x1024"
    assert call["quality"] == "medium"
    assert call["output_format"] == "png"
    assert call["moderation"] == "auto"
    assert call["background"] == "opaque"
    assert call["extra_body"] == {"safety_identifier": "nf_" + "a" * 64}
    assert "APPLICATION_IMAGE_SAFETY_CONTROLS" in call["prompt"]
    assert PRIVATE_PROMPT_TEXT in call["prompt"]
    assert API_KEY not in call["prompt"]


@pytest.mark.parametrize(
    ("output_format", "image_bytes", "media_type"),
    [
        (ImageOutputFormat.JPEG, b"\xff\xd8\xffsynthetic-jpeg", "image/jpeg"),
        (
            ImageOutputFormat.WEBP,
            b"RIFF\x10\x00\x00\x00WEBPsynthetic-webp",
            "image/webp",
        ),
    ],
)
def test_supported_jpeg_and_webp_responses_are_validated(
    output_format: ImageOutputFormat,
    image_bytes: bytes,
    media_type: str,
) -> None:
    client = FakeClient(successful_response(image_bytes=image_bytes))
    service = OpenAIImageGenerationService(
        configuration=configuration(),
        client=client,
    )

    result = run(service.generate(generation_request(output_format=output_format)))

    assert result.output_format == output_format
    assert result.image_data_reference.media_type == media_type
    assert result.image_data_reference.data is not None
    assert result.image_data_reference.data.get_secret_value() == image_bytes


def test_missing_credentials_fail_before_client_creation() -> None:
    called = False

    def client_factory(**kwargs: object) -> FakeClient:
        nonlocal called
        called = True
        return FakeClient(successful_response())

    with pytest.raises(OpenAIConfigurationError, match="OPENAI_API_KEY"):
        OpenAIImageGenerationService.from_settings(
            Settings(_env_file=None, openai_api_key=None),
            client_factory=client_factory,
        )

    assert called is False


def test_official_sdk_client_is_configured_without_automatic_retries() -> None:
    received: dict[str, object] = {}
    client = FakeClient(successful_response())

    def client_factory(**kwargs: object) -> FakeClient:
        received.update(kwargs)
        return client

    service = OpenAIImageGenerationService.from_settings(
        Settings(
            _env_file=None,
            openai_api_key=API_KEY,
            openai_image_model=MODEL,
            image_generation_timeout=75,
        ),
        client_factory=client_factory,
    )

    assert received == {"api_key": API_KEY, "timeout": 75, "max_retries": 0}
    run(service.close())
    assert client.closed is True


def test_safety_rejection_stops_before_provider_access() -> None:
    client = FakeClient(successful_response())
    service = OpenAIImageGenerationService(
        configuration=configuration(),
        client=client,
    )

    with pytest.raises(ImageGenerationSafetyDeniedError) as error:
        run(
            service.generate(
                generation_request(
                    safety_result=safety_result(ImageSafetyDecision.REJECTED)
                )
            )
        )

    assert error.value.code == "image_generation_safety_denied"
    assert client.images.calls == []


def test_rights_rejection_stops_before_provider_access() -> None:
    client = FakeClient(successful_response())
    service = OpenAIImageGenerationService(
        configuration=configuration(),
        client=client,
    )

    with pytest.raises(ImageGenerationRightsDeniedError) as error:
        run(
            service.generate(
                generation_request(rights_decision=rights_decision(allowed=False))
            )
        )

    assert error.value.code == "image_generation_rights_denied"
    assert client.images.calls == []


def test_timeout_is_controlled_and_not_automatically_replayed() -> None:
    provider_error = openai.APITimeoutError(
        httpx.Request("POST", "https://api.openai.com/v1/images/generations")
    )
    client = FakeClient(provider_error)
    service = OpenAIImageGenerationService(
        configuration=configuration(max_retries=2),
        client=client,
    )

    with pytest.raises(OpenAIImageTimeoutError) as error:
        run(service.generate(generation_request()))

    assert error.value.retryable is True
    assert len(client.images.calls) == 1


def test_rate_limit_is_retried_once_then_succeeds() -> None:
    rate_limit = status_error(
        openai.RateLimitError,
        429,
        headers={"retry-after": "2"},
    )
    client = FakeClient(rate_limit, successful_response())
    delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    service = OpenAIImageGenerationService(
        configuration=configuration(max_retries=1),
        client=client,
        sleep=fake_sleep,
    )

    result = run(service.generate(generation_request()))

    assert result.status == "completed"
    assert len(client.images.calls) == 2
    assert delays == [2]


def test_rate_limit_fails_after_bounded_retry_budget() -> None:
    errors = [status_error(openai.RateLimitError, 429) for _ in range(2)]
    client = FakeClient(*errors)

    async def no_wait(delay: float) -> None:
        assert delay == 0

    service = OpenAIImageGenerationService(
        configuration=configuration(max_retries=1),
        client=client,
        sleep=no_wait,
    )

    with pytest.raises(OpenAIImageRateLimitError) as error:
        run(service.generate(generation_request()))

    assert error.value.retryable is True
    assert len(client.images.calls) == 2


def test_quota_failure_is_not_retried() -> None:
    client = FakeClient(
        status_error(
            openai.RateLimitError,
            429,
            body={
                "error": {
                    "message": PROVIDER_DETAIL,
                    "type": "insufficient_quota",
                    "code": "insufficient_quota",
                }
            },
        )
    )
    service = OpenAIImageGenerationService(
        configuration=configuration(max_retries=2),
        client=client,
    )

    with pytest.raises(OpenAIImageQuotaError) as error:
        run(service.generate(generation_request()))

    assert error.value.retryable is False
    assert len(client.images.calls) == 1


def test_authentication_and_provider_details_are_never_exposed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = FakeClient(status_error(openai.AuthenticationError, 401))
    service = OpenAIImageGenerationService(
        configuration=configuration(),
        client=client,
    )

    with (
        caplog.at_level(logging.WARNING),
        pytest.raises(OpenAIImageAuthenticationError) as error,
    ):
        run(service.generate(generation_request()))

    combined = str(error.value) + caplog.text
    assert API_KEY not in combined
    assert PROVIDER_DETAIL not in combined
    assert PRIVATE_PROMPT_TEXT not in combined
    assert "Image service authentication failed." in str(error.value)


def test_connection_failure_maps_to_temporary_unavailability() -> None:
    provider_error = openai.APIConnectionError(
        message=PROVIDER_DETAIL,
        request=httpx.Request("POST", "https://api.openai.com/v1/images/generations"),
    )
    client = FakeClient(provider_error)
    service = OpenAIImageGenerationService(
        configuration=configuration(),
        client=client,
    )

    with pytest.raises(OpenAIImageUnavailableError) as error:
        run(service.generate(generation_request()))

    assert error.value.retryable is True
    assert len(client.images.calls) == 1


def test_provider_moderation_block_is_generic_and_not_retried() -> None:
    client = FakeClient(
        status_error(
            openai.BadRequestError,
            400,
            body={
                "error": {
                    "message": PROVIDER_DETAIL,
                    "type": "image_generation_user_error",
                    "code": "moderation_blocked",
                }
            },
        )
    )
    service = OpenAIImageGenerationService(
        configuration=configuration(max_retries=2),
        client=client,
    )

    with pytest.raises(OpenAIImageModerationError) as error:
        run(service.generate(generation_request()))

    assert error.value.code == "openai_image_moderation_blocked"
    assert error.value.retryable is False
    assert PROVIDER_DETAIL not in str(error.value)
    assert len(client.images.calls) == 1


@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(data=[], _request_id="req_empty", usage=None),
        SimpleNamespace(
            data=[SimpleNamespace(b64_json="not-base64", url=None)],
            _request_id="req_invalid_base64",
            usage=None,
        ),
        successful_response(image_bytes=b"not-a-png"),
        SimpleNamespace(
            data=[SimpleNamespace(b64_json=None, url="http://unsafe.example/image")],
            _request_id="req_unsafe_url",
            usage=None,
        ),
    ],
)
def test_invalid_provider_responses_fail_safely(response: object) -> None:
    client = FakeClient(response)
    service = OpenAIImageGenerationService(
        configuration=configuration(),
        client=client,
    )

    with pytest.raises(OpenAIImageInvalidResponseError) as error:
        run(service.generate(generation_request()))

    assert error.value.code == "openai_image_invalid_response"
    assert PRIVATE_PROMPT_TEXT not in str(error.value)


def test_https_provider_reference_uses_same_internal_interface() -> None:
    client = FakeClient(
        successful_response(url="https://images.example.invalid/temporary/image.png")
    )
    service = OpenAIImageGenerationService(
        configuration=configuration(),
        client=client,
    )

    result = run(service.generate(generation_request()))

    reference = result.image_data_reference
    assert reference.kind == ImageDataReferenceKind.PROVIDER_URL
    assert reference.data is None
    assert reference.retrieval_url is not None
    assert reference.retrieval_url.get_secret_value().startswith("https://")
    assert "images.example.invalid" not in repr(reference)


def test_duplicate_request_returns_cached_result_without_second_provider_call() -> None:
    client = FakeClient(successful_response())
    service = OpenAIImageGenerationService(
        configuration=configuration(),
        client=client,
    )
    request = generation_request()

    first = run(service.generate(request))
    second = run(service.generate(request))

    assert first == second
    assert len(client.images.calls) == 1


def test_request_id_reuse_with_different_input_is_rejected() -> None:
    client = FakeClient(successful_response())
    service = OpenAIImageGenerationService(
        configuration=configuration(),
        client=client,
    )
    run(service.generate(generation_request()))

    with pytest.raises(DuplicateImageGenerationError) as error:
        run(service.generate(generation_request(quality=ImageGenerationQuality.HIGH)))

    assert error.value.code == "image_generation_request_conflict"
    assert len(client.images.calls) == 1


def test_invalid_size_quality_safety_identifier_and_model_are_rejected() -> None:
    with pytest.raises(ValidationError, match="aspect ratio"):
        generation_request(size=ImageGenerationSize.LANDSCAPE)
    with pytest.raises(ValidationError):
        generation_request(quality="unbounded-quality")
    with pytest.raises(ValidationError, match="SHA-256"):
        generation_request(safety_identifier="someone@example.com")
    with pytest.raises(ValidationError, match="Unsupported OpenAI image model"):
        configuration(model="retired-image-model")


def test_missing_usage_is_returned_as_empty_bounded_metadata() -> None:
    client = FakeClient(successful_response(usage=None))
    service = OpenAIImageGenerationService(
        configuration=configuration(),
        client=client,
    )

    result = run(service.generate(generation_request()))

    assert result.usage_metadata.model_dump(exclude_none=True) == {}


def test_application_timeout_cancels_a_hanging_provider_call() -> None:
    class HangingImages:
        def __init__(self) -> None:
            self.calls = 0

        async def generate(self, **kwargs: Any) -> object:
            self.calls += 1
            await asyncio.sleep(1)
            return successful_response()

    client = FakeClient(successful_response())
    hanging = HangingImages()
    client.images = hanging  # type: ignore[assignment]
    service = OpenAIImageGenerationService(
        configuration=configuration(request_timeout_seconds=0.01),
        client=client,
    )

    with pytest.raises(OpenAIImageTimeoutError):
        run(service.generate(generation_request()))

    assert hanging.calls == 1


def test_request_ids_can_be_unique_for_separate_generation_attempts() -> None:
    client = FakeClient(successful_response(), successful_response())
    service = OpenAIImageGenerationService(
        configuration=configuration(),
        client=client,
    )

    first = run(service.generate(generation_request()))
    second = run(service.generate(generation_request(request_id=uuid4())))

    assert first.request_id != second.request_id
    assert len(client.images.calls) == 2
