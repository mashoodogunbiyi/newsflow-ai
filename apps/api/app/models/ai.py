"""Internal structured requests and results for AI text generation."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class AIJsonSchemaFormat(BaseModel):
    """Application-owned strict JSON schema requested from the AI provider."""

    name: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    schema_definition: dict[str, Any]

    model_config = ConfigDict(extra="forbid", frozen=True)


class AITextGenerationRequest(BaseModel):
    """Sensitive prompt data supplied by an authorised backend workflow."""

    input_text: SecretStr = Field(
        min_length=1,
        max_length=100_000,
        description="Authorised input text. Its representation is always masked.",
    )
    instructions: SecretStr | None = Field(
        default=None,
        min_length=1,
        max_length=20_000,
        description="Optional sensitive instructions for this generation.",
    )
    max_output_tokens: int | None = Field(default=None, ge=1, le=100_000)
    json_schema_format: AIJsonSchemaFormat | None = None

    @field_validator("input_text", "instructions")
    @classmethod
    def reject_blank_sensitive_text(
        cls,
        value: SecretStr | None,
    ) -> SecretStr | None:
        """Reject values that contain only whitespace without exposing them."""

        if value is not None and not value.get_secret_value().strip():
            raise ValueError("Sensitive generation text cannot be blank.")
        return value

    model_config = ConfigDict(extra="forbid")


class AITokenUsage(BaseModel):
    """Token counts returned by OpenAI when the provider makes them available."""

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class AITextGenerationResult(BaseModel):
    """Provider-neutral text and operational metadata returned to backend code."""

    text: str = Field(min_length=1)
    model: str = Field(min_length=1)
    response_id: str | None = None
    request_id: str | None = None
    usage: AITokenUsage

    model_config = ConfigDict(frozen=True)
