"""Reusable synthetic fixtures and mocked provider boundary for E5 tests."""

import base64
import io
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from PIL import Image

from app.providers.fixture_provider import DEFAULT_FIXTURES
from app.providers.models import NewsArticle
from app.providers.normalisation import ArticleNormalisationService

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "image_workflow_cases.json"
)


@dataclass(frozen=True)
class SyntheticImageFiles:
    """Isolated files generated under one pytest temporary directory."""

    valid_png: Path
    alternate_png: Path
    invalid_binary: Path
    corrupt_png: Path
    oversized_binary: Path


def load_image_cases() -> dict[str, Any]:
    """Load original synthetic scenarios committed for repeatable E5 testing."""

    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def synthetic_article(
    case: str = "permitted_technology",
    *,
    processing_allowed: bool = True,
) -> NewsArticle:
    """Return one validated article without live CNN or personal information."""

    selected = load_image_cases()["articles"][case]
    source = ArticleNormalisationService().normalise(DEFAULT_FIXTURES[0])
    values = source.model_dump(mode="json")
    values.update(
        {
            "title": selected["title"],
            "description": selected["description"],
            "category": selected["category"],
            "permitted_content": {
                "status": "available" if processing_allowed else "not_permitted",
                "content_type": "synthetic" if processing_allowed else "none",
                "text": selected["permitted_content"] if processing_allowed else None,
                "ai_processing_allowed": processing_allowed,
                "derivative_output_allowed": processing_allowed,
            },
        }
    )
    return NewsArticle.model_validate(values)


def generated_png(
    *,
    size: tuple[int, int] = (1536, 1024),
    colour: tuple[int, int, int] = (17, 91, 121),
) -> bytes:
    """Generate deterministic valid pixels without a provider or downloaded asset."""

    image = Image.new("RGB", size, color=colour)
    output = io.BytesIO()
    image.save(output, format="PNG")
    image.close()
    return output.getvalue()


def create_isolated_image_files(root: Path) -> SyntheticImageFiles:
    """Create valid, alternate, invalid, corrupt, and oversized test files."""

    root.mkdir(parents=True, exist_ok=True)
    cases = load_image_cases()["invalid_images"]
    paths = SyntheticImageFiles(
        valid_png=root / "valid-image.png",
        alternate_png=root / "alternate-image.png",
        invalid_binary=root / "invalid-image.bin",
        corrupt_png=root / "corrupt-image.png",
        oversized_binary=root / "oversized-image.bin",
    )
    paths.valid_png.write_bytes(generated_png())
    paths.alternate_png.write_bytes(generated_png(colour=(93, 44, 123)))
    paths.invalid_binary.write_text(cases["plain_text"], encoding="utf-8")
    paths.corrupt_png.write_bytes(bytes.fromhex(cases["truncated_png_hex"]))
    paths.oversized_binary.write_bytes(b"x" * 1_048_577)
    return paths


class MockImagesResource:
    """Deterministic replacement for `AsyncOpenAI().images`."""

    def __init__(self, image_bytes: bytes) -> None:
        self._image_bytes = image_bytes
        self.calls: list[dict[str, Any]] = []

    async def generate(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(
            data=[
                SimpleNamespace(
                    b64_json=base64.b64encode(self._image_bytes).decode("ascii"),
                    url=None,
                    revised_prompt="Synthetic revised text that is not retained.",
                )
            ],
            _request_id="synthetic-image-provider-request",
            model="synthetic-image-model",
            created=1_798_800_000,
            usage=SimpleNamespace(
                input_tokens=12,
                output_tokens=24,
                total_tokens=36,
                input_tokens_details=SimpleNamespace(
                    text_tokens=12,
                    image_tokens=0,
                ),
                output_tokens_details=SimpleNamespace(image_tokens=24),
            ),
        )


class MockOpenAIImageClient:
    """Mocked official-SDK client with no network capability."""

    def __init__(self, image_bytes: bytes) -> None:
        self.images = MockImagesResource(image_bytes)
        self.closed = False

    async def close(self) -> None:
        self.closed = True
