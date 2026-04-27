from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import HTTPException, status
from jwt import InvalidTokenError, PyJWKClient
from pydantic import BaseModel, ConfigDict, Field

from .config import Settings
from .models import AuthenticatedPrincipal
from .security import b64url_sha256, new_token_urlsafe, normalize_string_claims

LOGGER = logging.getLogger(__name__)


class OIDCMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    authorization_endpoint: str
    end_session_endpoint: str | None = None
    issuer: str
    jwks_uri: str
    token_endpoint: str
    userinfo_endpoint: str | None = None


class OIDCState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code_verifier: str = Field(min_length=43, max_length=128)
    nonce: str = Field(min_length=16, max_length=128)
    return_to: str
    state: str = Field(min_length=16, max_length=128)


class OIDCTokenResponse(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    access_token: str | None = None
    expires_in: int | None = None
    id_token: str
    refresh_token: str | None = None
    scope: str | None = None
    token_type: str


_metadata_cache: tuple[OIDCMetadata, float] | None = None
_jwks_clients: dict[str, PyJWKClient] = {}


def discovery_url(settings: Settings) -> str:
    issuer = settings.authentik_issuer.rstrip("/")
    if issuer.endswith(".well-known/openid-configuration"):
        return issuer
    return f"{issuer}/.well-known/openid-configuration"


async def get_oidc_metadata(settings: Settings) -> OIDCMetadata:
    global _metadata_cache

    now = time.monotonic()
    if _metadata_cache and _metadata_cache[1] > now:
        return _metadata_cache[0]

    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.get(discovery_url(settings), headers={"Accept": "application/json"})
        response.raise_for_status()

    metadata = OIDCMetadata.model_validate(response.json())
    _metadata_cache = (metadata, now + 300)
    return metadata


def issue_oidc_state_cookie(state: OIDCState, settings: Settings) -> str:
    now = int(time.time())
    payload = state.model_dump() | {
        "aud": "ctrlcontabil-oidc-state",
        "exp": now + settings.auth_state_ttl_seconds,
        "iat": now,
        "iss": "ctrlcontabil-api",
        "jti": new_token_urlsafe(16),
    }
    return jwt.encode(payload, settings.session_secret.get_secret_value(), algorithm="HS256")


def decode_oidc_state_cookie(token: str, settings: Settings) -> OIDCState:
    try:
        payload = jwt.decode(
            token,
            settings.session_secret.get_secret_value(),
            algorithms=["HS256"],
            audience="ctrlcontabil-oidc-state",
            issuer="ctrlcontabil-api",
            options={"require": ["aud", "exp", "iat", "iss", "jti", "state"]},
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado de autenticacao invalido.",
        ) from exc

    return OIDCState.model_validate(payload)


def build_authorization_url(metadata: OIDCMetadata, state: OIDCState, settings: Settings) -> str:
    params = {
        "client_id": settings.authentik_client_id,
        "code_challenge": b64url_sha256(state.code_verifier),
        "code_challenge_method": "S256",
        "nonce": state.nonce,
        "redirect_uri": f"{settings.api_base_url.rstrip('/')}/auth/callback",
        "response_type": "code",
        "scope": settings.oidc_scopes,
        "state": state.state,
    }
    return f"{metadata.authorization_endpoint}?{urlencode(params)}"


async def exchange_authorization_code(
    *,
    code: str,
    metadata: OIDCMetadata,
    oidc_state: OIDCState,
    settings: Settings,
) -> OIDCTokenResponse:
    data = {
        "client_id": settings.authentik_client_id,
        "code": code,
        "code_verifier": oidc_state.code_verifier,
        "grant_type": "authorization_code",
        "redirect_uri": f"{settings.api_base_url.rstrip('/')}/auth/callback",
    }

    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.post(
            metadata.token_endpoint,
            auth=httpx.BasicAuth(
                settings.authentik_client_id,
                settings.authentik_client_secret.get_secret_value(),
            ),
            data=data,
            headers={"Accept": "application/json"},
        )

    if response.status_code >= 400:
        LOGGER.warning("OIDC token exchange failed with status %s", response.status_code)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falha na autenticacao.",
        )

    return OIDCTokenResponse.model_validate(response.json())


async def verify_authentik_jwt(
    token: str,
    *,
    settings: Settings,
    expected_nonce: str | None = None,
) -> dict[str, Any]:
    metadata = await get_oidc_metadata(settings)
    jwks_client = _jwks_clients.setdefault(metadata.jwks_uri, PyJWKClient(metadata.jwks_uri))

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=settings.authentik_algorithms,
            audience=settings.authentik_client_id,
            issuer=metadata.issuer,
            options={"require": ["aud", "exp", "iat", "iss", "sub"]},
        )
    except InvalidTokenError as exc:
        LOGGER.info("Rejected invalid Authentik JWT: %s", exc.__class__.__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido.",
        ) from exc

    if expected_nonce is not None and payload.get("nonce") != expected_nonce:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nonce invalido.",
        )

    return payload


def principal_from_claims(claims: dict[str, Any]) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        sub=str(claims["sub"]),
        email=claims.get("email"),
        groups=normalize_string_claims(claims.get("groups")),
        name=claims.get("name"),
        preferred_username=claims.get("preferred_username"),
        roles=normalize_string_claims(claims.get("roles") or claims.get("entitlements")),
        sid=claims.get("sid"),
    )


async def end_session_url(settings: Settings, return_to: str) -> str:
    metadata = await get_oidc_metadata(settings)
    endpoint = metadata.end_session_endpoint
    if not endpoint:
        endpoint = f"{settings.authentik_issuer.rstrip('/')}/end-session/"
    return f"{endpoint}?{urlencode({'post_logout_redirect_uri': return_to})}"
