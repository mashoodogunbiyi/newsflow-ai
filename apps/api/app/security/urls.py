"""Conservative validation for provider-controlled external HTTPS URLs."""

import ipaddress
from urllib.parse import urlsplit

BLOCKED_HOSTNAMES = frozenset({"localhost", "localhost.localdomain"})
BLOCKED_HOST_SUFFIXES = (
    ".example",
    ".internal",
    ".invalid",
    ".local",
    ".localhost",
    ".test",
)


def is_safe_external_https_url(value: str) -> bool:
    """Reject URL forms that could address credentials or local/private services."""

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or port not in {None, 443}
    ):
        return False

    try:
        hostname = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError:
        return False
    if (
        not hostname
        or hostname in BLOCKED_HOSTNAMES
        or hostname.endswith(BLOCKED_HOST_SUFFIXES)
        or "." not in hostname
        or "%" in hostname
    ):
        return False

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        if all(character.isdigit() or character == "." for character in hostname):
            return False
        return True
    return address.is_global
