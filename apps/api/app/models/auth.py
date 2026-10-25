"""Validated registration request and safe response schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

MINIMUM_PASSWORD_LENGTH = 12
MAXIMUM_PASSWORD_LENGTH = 128

COMMON_PASSWORDS = {
    "password123!",
    "qwerty123456!",
    "welcome12345!",
    "letmein12345!",
}


class RegisterUserRequest(BaseModel):
    """Credentials required to create the minimum user account."""

    email: EmailStr = Field(description="Email address used to identify the account.")
    password: SecretStr = Field(
        min_length=MINIMUM_PASSWORD_LENGTH,
        max_length=MAXIMUM_PASSWORD_LENGTH,
        description=(
            "A 12 to 128 character password containing uppercase, lowercase, "
            "number, and symbol characters."
        ),
    )

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, value: object) -> object:
        """Remove accidental surrounding whitespace before email validation."""

        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        """Match the lowercase email invariant enforced by PostgreSQL."""

        return str(value).lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: SecretStr) -> SecretStr:
        """Enforce the documented NFA-22 password composition rules."""

        password = value.get_secret_value()
        requirements = (
            (any(character.islower() for character in password), "lowercase letter"),
            (any(character.isupper() for character in password), "uppercase letter"),
            (any(character.isdigit() for character in password), "number"),
            (
                any(
                    not character.isalnum() and not character.isspace()
                    for character in password
                ),
                "symbol",
            ),
        )
        missing = [name for present, name in requirements if not present]
        if missing:
            raise ValueError(
                "Password must contain at least one " + ", ".join(missing) + "."
            )
        if password.casefold() in COMMON_PASSWORDS:
            raise ValueError("Password is too common.")
        return value

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "email": "example@email.com",
                    "password": "ExampleSecurePassword123!",
                }
            ]
        },
    )


class RegisterUserResponse(BaseModel):
    """Public account fields returned after successful registration."""

    id: UUID
    email: EmailStr
    message: str = "Account created successfully"
