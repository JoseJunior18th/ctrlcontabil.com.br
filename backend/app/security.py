from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import jwt
from fastapi import HTTPException, Request, status
from jwt import InvalidTokenError

from .config import Settings
from .models import AuthenticatedPrincipal
from .sanitization import sanitize_plain_text

LOGGER = logging.getLogger(__name__)


def b64url_sha256(value: str) -> str:
    digest = hashlib.sha256(value.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def new_token_urlsafe(bytes_size: int = 32) -> str:
    return secrets.token_urlsafe(bytes_size)


def normalize_string_claims(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (sanitize_plain_text(value, max_length=120, allow_markup=False),)
    if isinstance(value, Iterable):
        output: list[str] = []
        for item in value:
            if isinstance(item, str):
                output.append(sanitize_plain_text(item, max_length=120, allow_markup=False))
        return tuple(dict.fromkeys(output))
    return ()


def safe_redirect_target(return_to: str | None, settings: Settings) -> str:
    fallback = urljoin(settings.frontend_base_url.rstrip("/") + "/", "app")
    if not return_to:
        return fallback

    if return_to.startswith("/") and not return_to.startswith("//"):
        return urljoin(settings.frontend_base_url.rstrip("/") + "/", return_to.lstrip("/"))

    parsed = urlparse(return_to)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return fallback

    hostname = parsed.hostname or ""
    is_local = hostname in {"localhost", "127.0.0.1"}
    if parsed.scheme != "https" and not is_local:
        return fallback

    if hostname not in settings.allowed_return_hosts:
        return fallback

    return return_to


def issue_session_token(principal: AuthenticatedPrincipal, settings: Settings) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "aud": "ctrlcontabil-web",
        "email": str(principal.email) if principal.email else None,
        "exp": now + settings.session_ttl_seconds,
        "groups": list(principal.groups),
        "iat": now,
        "iss": "ctrlcontabil-api",
        "jti": new_token_urlsafe(16),
        "name": principal.name,
        "preferred_username": principal.preferred_username,
        "roles": list(principal.roles),
        "sid": principal.sid,
        "sub": principal.sub,
    }
    return jwt.encode(payload, settings.session_secret.get_secret_value(), algorithm="HS256")


def principal_from_session_token(token: str, settings: Settings) -> AuthenticatedPrincipal:
    try:
        payload = jwt.decode(
            token,
            settings.session_secret.get_secret_value(),
            algorithms=["HS256"],
            audience="ctrlcontabil-web",
            issuer="ctrlcontabil-api",
            options={"require": ["aud", "exp", "iat", "iss", "jti", "sub"]},
        )
    except InvalidTokenError as exc:
        LOGGER.info("Rejected invalid local session token: %s", exc.__class__.__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao invalida.",
        ) from exc

    return AuthenticatedPrincipal(
        sub=payload["sub"],
        email=payload.get("email"),
        groups=normalize_string_claims(payload.get("groups")),
        name=payload.get("name"),
        preferred_username=payload.get("preferred_username"),
        roles=normalize_string_claims(payload.get("roles")),
        sid=payload.get("sid"),
    )


def set_session_cookie(response: Any, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
        domain=settings.session_cookie_domain,
    )


def clear_session_cookie(response: Any, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        domain=settings.session_cookie_domain,
    )


@dataclass
class RateLimitBucket:
    count: int
    reset_at: float


class InMemoryRateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, RateLimitBucket] = {}

    def check(self, key: str) -> int | None:
        now = time.monotonic()
        bucket = self._buckets.get(key)

        if bucket is None or bucket.reset_at <= now:
            self._buckets[key] = RateLimitBucket(count=1, reset_at=now + self.window_seconds)
            return None

        bucket.count += 1
        if bucket.count > self.max_requests:
            return max(1, int(bucket.reset_at - now))

        return None

    def cleanup(self) -> None:
        now = time.monotonic()
        stale_keys = [key for key, bucket in self._buckets.items() if bucket.reset_at <= now]
        for key in stale_keys:
            del self._buckets[key]


def rate_limit_key(request: Request) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{request.method}:{request.url.path}"
