"""Content-based validation and metadata removal for generated images."""

import hashlib
import io
import warnings

from PIL import Image, UnidentifiedImageError

from app.core.image_storage_config import ImageStorageConfiguration
from app.models.generated_image import ValidatedGeneratedImage

FORMAT_DETAILS = {
    "PNG": ("image/png", "png"),
    "JPEG": ("image/jpeg", "jpg"),
    "WEBP": ("image/webp", "webp"),
}


class GeneratedImageValidationError(RuntimeError):
    """Safe validation failure with a stable caller-facing code."""

    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.safe_message = message
        super().__init__(message)


class GeneratedImageValidationService:
    """Verify actual image content and produce metadata-free canonical bytes."""

    def __init__(self, configuration: ImageStorageConfiguration) -> None:
        self._configuration = configuration

    def validate(
        self,
        image_bytes: bytes,
        *,
        expected_media_type: str,
        expected_dimensions: tuple[int, int],
    ) -> ValidatedGeneratedImage:
        """Reject invalid content and re-encode accepted pixels without metadata."""

        if not image_bytes:
            self._reject("image_empty", "Generated image data is empty.")
        if len(image_bytes) > self._configuration.max_file_bytes:
            self._reject(
                "image_too_large", "Generated image exceeds the file-size limit."
            )

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(image_bytes)) as probe:
                    detected_format = probe.format
                    width, height = probe.size
                    frame_count = getattr(probe, "n_frames", 1)
                    probe.verify()
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
            raise GeneratedImageValidationError(
                code="image_corrupt",
                message="Generated image data is corrupt or unsupported.",
            ) from exc
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise GeneratedImageValidationError(
                code="image_pixel_limit_exceeded",
                message="Generated image exceeds the safe pixel limit.",
            ) from exc

        if detected_format not in FORMAT_DETAILS:
            self._reject(
                "image_format_unsupported", "Generated image format is not supported."
            )
        detected_media_type, file_extension = FORMAT_DETAILS[detected_format]
        if detected_media_type != expected_media_type:
            self._reject(
                "image_media_type_mismatch",
                "Generated image content does not match its declared media type.",
            )
        if frame_count != 1:
            self._reject(
                "image_animation_unsupported", "Animated images are not supported."
            )
        if (width, height) != expected_dimensions:
            self._reject(
                "image_dimensions_mismatch",
                "Generated image dimensions do not match the requested dimensions.",
            )
        if (width, height) not in self._configuration.supported_dimensions:
            self._reject(
                "image_dimensions_unsupported",
                "Generated image dimensions are not supported.",
            )
        if width * height > self._configuration.max_pixels:
            self._reject(
                "image_pixel_limit_exceeded",
                "Generated image exceeds the safe pixel limit.",
            )

        canonical = self._remove_metadata(
            image_bytes,
            detected_format=detected_format,
        )
        if len(canonical) > self._configuration.max_file_bytes:
            self._reject(
                "image_too_large",
                "Canonical generated image exceeds the file-size limit.",
            )
        return ValidatedGeneratedImage(
            data=canonical,
            mime_type=detected_media_type,
            file_extension=file_extension,
            width=width,
            height=height,
            file_size_bytes=len(canonical),
            sha256=hashlib.sha256(canonical).hexdigest(),
            metadata_removed=True,
        )

    @staticmethod
    def _remove_metadata(image_bytes: bytes, *, detected_format: str) -> bytes:
        """Re-encode pixels only, omitting EXIF, comments, and source metadata."""

        try:
            with Image.open(io.BytesIO(image_bytes)) as source:
                source.load()
                has_alpha = "A" in source.getbands()
                if detected_format == "JPEG":
                    clean = source.convert("RGB")
                    options = {"format": "JPEG", "quality": 95, "optimize": True}
                elif detected_format == "WEBP":
                    clean = source.convert("RGBA" if has_alpha else "RGB")
                    options = {"format": "WEBP", "quality": 95, "method": 4}
                else:
                    clean = source.convert("RGBA" if has_alpha else "RGB")
                    options = {"format": "PNG", "optimize": True}
                output = io.BytesIO()
                clean.save(output, **options)
                clean.close()
                return output.getvalue()
        except (OSError, ValueError) as exc:
            raise GeneratedImageValidationError(
                code="image_processing_failed",
                message="Generated image could not be processed safely.",
            ) from exc

    @staticmethod
    def _reject(code: str, message: str) -> None:
        raise GeneratedImageValidationError(code=code, message=message)
