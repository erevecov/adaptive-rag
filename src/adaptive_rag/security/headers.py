"""ASGI middleware that attaches baseline security headers."""

from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "X-Permitted-Cross-Domain-Policies": "none",
}


class SecurityHeadersMiddleware:
    """Append baseline security headers to every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                existing = {
                    name.decode("latin-1").lower() for name, _ in headers
                }
                for name, value in SECURITY_HEADERS.items():
                    if name.lower() not in existing:
                        headers.append(
                            (name.lower().encode("latin-1"), value.encode("latin-1"))
                        )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)
