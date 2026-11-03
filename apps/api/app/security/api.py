"""API boundary controls for request and response hardening."""

from __future__ import annotations

import json

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

STATE_CHANGING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
DOCUMENTATION_PATHS = frozenset(
    {"/docs", "/docs/oauth2-redirect", "/openapi.json", "/redoc"}
)


class ApiSecurityMiddleware:
    """Apply bounded request parsing and consistent API response protections."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_request_body_bytes: int,
        hsts_enabled: bool,
    ) -> None:
        self._app = app
        self._max_request_body_bytes = max_request_body_bytes
        self._hsts_enabled = hsts_enabled

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path = str(scope.get("path", ""))
        method = str(scope.get("method", "GET")).upper()
        headers = Headers(scope=scope)
        content_length = self._content_length(headers)
        if content_length is None:
            await self._send_error(
                send,
                path=path,
                status_code=400,
                code="invalid_content_length",
                message="The Content-Length header is invalid.",
            )
            return
        if content_length > self._max_request_body_bytes:
            await self._send_too_large(send, path=path)
            return

        buffered_messages: list[Message] | None = None
        if method in STATE_CHANGING_METHODS:
            bounded_body = await self._bounded_body(receive)
            if bounded_body is None:
                await self._send_too_large(send, path=path)
                return
            buffered_messages, received_bytes = bounded_body
            if received_bytes and not self._is_json_content_type(
                headers.get("content-type")
            ):
                await self._send_error(
                    send,
                    path=path,
                    status_code=415,
                    code="unsupported_media_type",
                    message="Request bodies must use application/json.",
                )
                return

        async def replay_receive() -> Message:
            if buffered_messages:
                return buffered_messages.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        async def secure_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                self._apply_response_headers(
                    MutableHeaders(scope=message),
                    path=path,
                )
            await send(message)

        await self._app(
            scope,
            replay_receive if buffered_messages is not None else receive,
            secure_send,
        )

    @staticmethod
    def _content_length(headers: Headers) -> int | None:
        raw_value = headers.get("content-length")
        if raw_value is None:
            return 0
        try:
            value = int(raw_value)
        except ValueError:
            return None
        return value if value >= 0 else None

    @staticmethod
    def _is_json_content_type(content_type: str | None) -> bool:
        if content_type is None:
            return False
        media_type = content_type.partition(";")[0].strip().lower()
        return media_type == "application/json" or media_type.endswith("+json")

    async def _bounded_body(
        self,
        receive: Receive,
    ) -> tuple[list[Message], int] | None:
        messages: list[Message] = []
        total_bytes = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                return messages, total_bytes
            total_bytes += len(message.get("body", b""))
            if total_bytes > self._max_request_body_bytes:
                return None
            if not message.get("more_body", False):
                return messages, total_bytes

    async def _send_too_large(self, send: Send, *, path: str) -> None:
        await self._send_error(
            send,
            path=path,
            status_code=413,
            code="request_body_too_large",
            message="The request body exceeds the configured size limit.",
        )

    async def _send_error(
        self,
        send: Send,
        *,
        path: str,
        status_code: int,
        code: str,
        message: str,
    ) -> None:
        body = json.dumps(
            {"error": {"code": code, "message": message}},
            separators=(",", ":"),
        ).encode("utf-8")
        start: Message = {
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
        self._apply_response_headers(MutableHeaders(scope=start), path=path)
        await send(start)
        await send({"type": "http.response.body", "body": body})

    def _apply_response_headers(self, headers: MutableHeaders, *, path: str) -> None:
        protected_headers: dict[str, str] = {
            "Cache-Control": "no-store",
            "Cross-Origin-Resource-Policy": "same-site",
            "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-Permitted-Cross-Domain-Policies": "none",
        }
        if path not in DOCUMENTATION_PATHS:
            protected_headers["Content-Security-Policy"] = (
                "default-src 'none'; base-uri 'none'; frame-ancestors 'none'"
            )
        if self._hsts_enabled:
            protected_headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        for name, value in protected_headers.items():
            if name not in headers:
                headers[name] = value
