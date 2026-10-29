"""Safe provider errors that do not expose credentials or raw responses."""

from enum import Enum


class ProviderErrorCode(str, Enum):
    """Stable error codes understood outside provider implementations."""

    SOURCE_NOT_AUTHORISED = "SOURCE_NOT_AUTHORISED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_DATA_INVALID = "PROVIDER_DATA_INVALID"
    INVALID_PROVIDER_CURSOR = "INVALID_PROVIDER_CURSOR"
    ARTICLE_NOT_FOUND = "ARTICLE_NOT_FOUND"


class ProviderError(RuntimeError):
    """Base failure with a safe message and retry classification."""

    def __init__(
        self,
        *,
        code: ProviderErrorCode,
        message: str,
        retryable: bool,
    ) -> None:
        self.code = code
        self.safe_message = message
        self.retryable = retryable
        super().__init__(message)


class SourceNotAuthorisedError(ProviderError):
    """Raised before access when no approved source profile is enabled."""

    def __init__(self) -> None:
        super().__init__(
            code=ProviderErrorCode.SOURCE_NOT_AUTHORISED,
            message="The requested news source is not authorised.",
            retryable=False,
        )


class ProviderUnavailableError(ProviderError):
    """Raised for a temporary provider failure."""

    def __init__(self) -> None:
        super().__init__(
            code=ProviderErrorCode.PROVIDER_UNAVAILABLE,
            message="The news provider is temporarily unavailable.",
            retryable=True,
        )


class ProviderDataError(ProviderError):
    """Raised when provider data cannot satisfy the approved contract."""

    def __init__(self, source_item_id: str | None = None) -> None:
        item_reference = f" for item {source_item_id}" if source_item_id else ""
        super().__init__(
            code=ProviderErrorCode.PROVIDER_DATA_INVALID,
            message=f"The news provider returned invalid data{item_reference}.",
            retryable=False,
        )


class InvalidProviderCursorError(ProviderError):
    """Raised when an opaque pagination bookmark cannot be used."""

    def __init__(self) -> None:
        super().__init__(
            code=ProviderErrorCode.INVALID_PROVIDER_CURSOR,
            message="The news-provider pagination cursor is invalid.",
            retryable=False,
        )


class ArticleNotFoundError(ProviderError):
    """Raised when a provider has no article with the requested identifier."""

    def __init__(self) -> None:
        super().__init__(
            code=ProviderErrorCode.ARTICLE_NOT_FOUND,
            message="The requested news article was not found.",
            retryable=False,
        )
