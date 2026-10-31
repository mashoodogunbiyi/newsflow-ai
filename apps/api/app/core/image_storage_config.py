"""Bounded configuration for generated-image validation and private storage."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ImageStorageConfiguration(BaseModel):
    """Validated limits and local private-storage location."""

    backend: Literal["local"] = "local"
    local_root: Path
    max_file_bytes: int = Field(10_485_760, ge=1_048_576, le=26_214_400)
    max_pixels: int = Field(4_000_000, ge=1_048_576, le=16_777_216)
    supported_dimensions: frozenset[tuple[int, int]] = frozenset(
        {
            (1024, 1024),
            (1536, 1024),
            (1024, 1536),
        }
    )

    model_config = ConfigDict(extra="forbid", frozen=True)
