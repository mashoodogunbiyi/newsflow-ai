"""NFA-51 content-based generated-image validation tests."""

import io

import pytest
from PIL import Image, PngImagePlugin

from app.core.image_storage_config import ImageStorageConfiguration
from app.services.image_validation import (
    GeneratedImageValidationError,
    GeneratedImageValidationService,
)


def png_bytes(
    *,
    size: tuple[int, int] = (16, 16),
    comment: str | None = None,
) -> bytes:
    image = Image.new("RGB", size, color=(24, 85, 120))
    output = io.BytesIO()
    metadata = None
    if comment is not None:
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Comment", comment)
    image.save(output, format="PNG", pnginfo=metadata)
    image.close()
    return output.getvalue()


def validator(**overrides: object) -> GeneratedImageValidationService:
    values: dict[str, object] = {
        "local_root": ".local/test-image-storage",
        "max_file_bytes": 1_048_576,
        "max_pixels": 1_048_576,
        "supported_dimensions": frozenset({(16, 16), (32, 16)}),
    }
    values.update(overrides)
    return GeneratedImageValidationService(
        ImageStorageConfiguration.model_validate(values)
    )


def test_valid_image_is_detected_from_content_and_sensitive_metadata_is_removed() -> (
    None
):
    original = png_bytes(comment="private source annotation")

    result = validator().validate(
        original,
        expected_media_type="image/png",
        expected_dimensions=(16, 16),
    )

    assert result.mime_type == "image/png"
    assert result.file_extension == "png"
    assert (result.width, result.height) == (16, 16)
    assert result.metadata_removed is True
    with Image.open(io.BytesIO(result.data.get_secret_value())) as cleaned:
        assert cleaned.format == "PNG"
        assert "Comment" not in cleaned.info
        assert "exif" not in cleaned.info


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (b"plain text pretending to be an image", "image_corrupt"),
        (png_bytes()[:20], "image_corrupt"),
    ],
)
def test_invalid_or_corrupt_image_is_rejected(payload: bytes, code: str) -> None:
    with pytest.raises(GeneratedImageValidationError) as error:
        validator().validate(
            payload,
            expected_media_type="image/png",
            expected_dimensions=(16, 16),
        )

    assert error.value.code == code


def test_declared_media_type_must_match_actual_content() -> None:
    with pytest.raises(GeneratedImageValidationError) as error:
        validator().validate(
            png_bytes(),
            expected_media_type="image/jpeg",
            expected_dimensions=(16, 16),
        )

    assert error.value.code == "image_media_type_mismatch"


def test_requested_dimensions_must_match_actual_dimensions() -> None:
    with pytest.raises(GeneratedImageValidationError) as error:
        validator().validate(
            png_bytes(size=(32, 16)),
            expected_media_type="image/png",
            expected_dimensions=(16, 16),
        )

    assert error.value.code == "image_dimensions_mismatch"


def test_oversized_payload_is_rejected_before_decoding() -> None:
    oversized = png_bytes() + (b"x" * 1_048_576)

    with pytest.raises(GeneratedImageValidationError) as error:
        validator().validate(
            oversized,
            expected_media_type="image/png",
            expected_dimensions=(16, 16),
        )

    assert error.value.code == "image_too_large"
