"""Validated backend-only configuration for OpenAI image generation."""

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

SUPPORTED_OPENAI_IMAGE_MODELS = frozenset(
    {
        "gpt-image-2.5-flare",
        "gpt-image-2.5-flare-2026-09-08",
        "gpt-image-2.5-sunburst",
        "gpt-image-2.5-sunburst-2026-09-08",
    }
)


class OpenAIImageGenerationConfiguration(BaseModel):
    """Immutable limits used to initialise one image-generation client."""

    api_key: SecretStr = Field(repr=False)
    model: str = Field(min_length=1, max_length=200)
    request_timeout_seconds: float = Field(ge=0.01, le=300)
    max_concurrent_requests: int = Field(ge=1, le=10)
    max_retries: int = Field(ge=0, le=2)
    retry_base_seconds: float = Field(ge=0, le=10)
    max_response_bytes: int = Field(ge=1_048_576, le=52_428_800)
    duplicate_cache_size: int = Field(ge=1, le=1_000)

    @field_validator("model")
    @classmethod
    def require_supported_image_model(cls, value: str) -> str:
        """Fail closed until a newly available model is explicitly reviewed."""

        if value not in SUPPORTED_OPENAI_IMAGE_MODELS:
            supported = ", ".join(sorted(SUPPORTED_OPENAI_IMAGE_MODELS))
            raise ValueError(f"Unsupported OpenAI image model. Supported: {supported}.")
        return value

    model_config = ConfigDict(extra="forbid", frozen=True)
