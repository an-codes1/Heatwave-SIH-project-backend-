"""API security helpers: the admin-key dependency and security headers.

The admin key comes exclusively from the environment
(``ADMIN_API_KEY``). It is never hardcoded, logged, or returned in
error responses. Comparison uses a constant-time digest.
"""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import Header, HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

ADMIN_HEADER = "X-Admin-Key"

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": (
        "camera=(), geolocation=(), microphone=()"
    ),
}


def mask_sensitive(value: str | None) -> str:
    """Mask a recipient identifier for logs without revealing it."""
    if value is None:
        return "<none>"
    value = str(value).strip()
    if len(value) <= 6:
        return "<masked>"
    return f"{value[:2]}***{value[-2:]}"


def require_admin(
    x_admin_key: str | None = Header(default=None, alias=ADMIN_HEADER),
) -> None:
    """Reject requests that lack a valid environment-configured admin key.

    - header missing  -> 401
    - key not set / wrong -> 401 / 403
    - correct key     -> request proceeds (this dependency returns None)
    """

    expected = settings.admin_api_key

    if not expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrative access is not configured.",
        )

    if x_admin_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin key missing.",
        )

    if not secrets.compare_digest(
        x_admin_key.encode("utf-8"),
        expected.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key.",
        )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add lightweight security headers to every response."""

    async def dispatch(
        self,
        request: Request,
        call_next: Any,
    ) -> Response:
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response