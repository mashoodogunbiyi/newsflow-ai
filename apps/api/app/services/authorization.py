"""Reusable object-level authorisation rules for private resources."""

from typing import TypeVar

OwnedResource = TypeVar("OwnedResource")


class PrivateResourceNotFoundError(RuntimeError):
    """Hide whether a private resource exists for a different user."""


def require_owned_resource(resource: OwnedResource | None) -> OwnedResource:
    """Return an owner-scoped result or the standard private-resource outcome."""

    if resource is None:
        raise PrivateResourceNotFoundError(
            "The requested resource was not found for the authenticated user."
        )
    return resource
