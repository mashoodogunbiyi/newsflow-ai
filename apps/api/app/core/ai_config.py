"""Validated, secret-safe configuration for the OpenAI service."""

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class OpenAIServiceConfiguration(BaseModel):
    """Immutable limits and credentials used to initialise one SDK client."""

    api_key: SecretStr = Field(repr=False)
    model: str = Field(min_length=1, max_length=200)
    request_timeout: float = Field(ge=1.0, le=300.0)
    max_output_tokens: int = Field(ge=1, le=100_000)
    max_retries: int = Field(ge=0, le=5)

    model_config = ConfigDict(frozen=True)
