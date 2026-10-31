"""Private image-storage abstraction and secure local development adapter."""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from app.models.generated_image import PrivateImageObject


class PrivateImageStorageError(RuntimeError):
    """Raised without revealing a filesystem path or storage credential."""


class PrivateImageObjectNotFoundError(PrivateImageStorageError):
    """Raised when an authorised private object no longer exists."""


class PrivateImageStorage(Protocol):
    """Backend-only object operations with no public URL operation."""

    async def put(self, data: bytes, *, file_extension: str) -> PrivateImageObject: ...

    async def delete(self, storage_key: str) -> None: ...

    async def read(self, storage_key: str) -> bytes: ...


class LocalPrivateImageStorage:
    """Private local adapter for development and test environments."""

    def __init__(self, root: Path) -> None:
        self._root = root.expanduser().resolve()

    async def put(self, data: bytes, *, file_extension: str) -> PrivateImageObject:
        """Atomically write bytes under an unpredictable server-generated key."""

        if file_extension not in {"png", "jpg", "webp"}:
            raise PrivateImageStorageError("Image storage format is unsupported.")
        return await asyncio.to_thread(self._put_sync, data, file_extension)

    async def delete(self, storage_key: str) -> None:
        """Remove an internal object during compensation or lifecycle deletion."""

        await asyncio.to_thread(self._delete_sync, storage_key)

    async def read(self, storage_key: str) -> bytes:
        """Read an object for an already-authorised backend workflow."""

        return await asyncio.to_thread(self._read_sync, storage_key)

    def _put_sync(self, data: bytes, file_extension: str) -> PrivateImageObject:
        target_directory = self._root / "generated-images"
        try:
            target_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(self._root, 0o700)
            os.chmod(target_directory, 0o700)
            storage_key = f"generated-images/{uuid4().hex}.{file_extension}"
            target = self._resolve_key(storage_key)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".upload-",
                dir=target_directory,
            )
            try:
                os.fchmod(descriptor, 0o600)
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary_name, target)
                os.chmod(target, 0o600)
            except BaseException:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                Path(temporary_name).unlink(missing_ok=True)
                raise
        except OSError as exc:
            raise PrivateImageStorageError(
                "Generated image could not be written to private storage."
            ) from exc
        return PrivateImageObject(
            provider="local_private",
            storage_key=storage_key,
            file_size_bytes=len(data),
        )

    def _delete_sync(self, storage_key: str) -> None:
        try:
            self._resolve_key(storage_key).unlink(missing_ok=True)
        except OSError as exc:
            raise PrivateImageStorageError(
                "Generated image could not be removed from private storage."
            ) from exc

    def _read_sync(self, storage_key: str) -> bytes:
        try:
            return self._resolve_key(storage_key).read_bytes()
        except FileNotFoundError as exc:
            raise PrivateImageObjectNotFoundError(
                "Generated image is missing from private storage."
            ) from exc
        except OSError as exc:
            raise PrivateImageStorageError(
                "Generated image could not be read from private storage."
            ) from exc

    def _resolve_key(self, storage_key: str) -> Path:
        candidate = (self._root / storage_key).resolve()
        if not candidate.is_relative_to(self._root):
            raise PrivateImageStorageError("Private storage key is invalid.")
        return candidate
