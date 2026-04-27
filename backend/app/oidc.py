from __future__ import annotations

import logging
import time
from typing import Any, cast
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import HTTPException, status
from jwt import InvalidTokenError, PyJWK
from pydantic import BaseModel, ConfigDict, Field, ValidationError

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
    model_config = ConfigDict(extra="ignore", frozen=True)

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
_jwks_cache: dict[str, tuple[dict[str, Any], float]] = {}


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

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.get(
                discovery_url(settings),
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()

        metadata = OIDCMetadata.model_validate(response.json())
    except (httpx.HTTPError, ValidationError) as exc:
        LOGGER.warning("OIDC discovery failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Provedor de autenticacao indisponivel.",
        ) from exc

    _metadata_cache = (metadata, now + 300)
    return metadata


async def get_jwks(metadata: OIDCMetadata, settings: Settings) -> dict[str, Any]:
    now = time.monotonic()
    cached = _jwks_cache.get(metadata.jwks_uri)
    if cached and cached[1] > now:
        return cached[0]

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.get(metadata.jwks_uri, headers={"Accept": "application/json"})
            response.raise_for_status()

        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        LOGGER.warning("OIDC JWKS fetch failed from %s: %s", metadata.jwks_uri, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chaves do provedor de autenticacao indisponiveis.",
        ) from exc

    if not isinstance(data, dict):
        LOGGER.warning("OIDC JWKS response from %s was not an object.", metadata.jwks_uri)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chaves do provedor de autenticacao invalidas.",
        )

    jwks = cast(dict[str, Any], data)
    _jwks_cache[metadata.jwks_uri] = (jwks, now + 300)
    return jwks


def signing_key_from_jwks(token: str, jwks: dict[str, Any]) -> Any:
    try:
        header = jwt.get_unverified_header(token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido.",
        ) from exc

    token_kid = header.get("kid")
    token_alg = header.get("alg")
    keys = jwks.get("keys")
    if not isinstance(keys, list):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chaves do provedor de autenticacao invalidas.",
        )

    for key_data in keys:
        if not isinstance(key_data, dict):
            continue
        if token_kid and key_data.get("kid") != token_kid:
            continue
        if token_alg and key_data.get("alg") and key_data.get("alg") != token_alg:
            continue
        return PyJWK.from_dict(key_data, algorithm=token_alg).key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Chave de assinatura do token nao encontrada.",
    )


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

    try:
        return OIDCState.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado de autenticacao invalido.",
        ) from exc


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


def _jwt_diagnostic(token: str) -> str:
    segment_count = token.count(".") + 1
    try:
        header = jwt.get_unverified_header(token)
    except InvalidTokenError as exc:
        return f"segments={segment_count} header_error={exc.__class__.__name__}"

    alg = header.get("alg")
    kid = header.get("kid")
    typ = header.get("typ")
    enc = header.get("enc")
    return f"segments={segment_count} alg={alg!r} typ={typ!r} kid={kid!r} enc={enc!r}"


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

    try:
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
    except httpx.HTTPError as exc:
        LOGGER.warning("OIDC token exchange request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Provedor de autenticacao indisponivel.",
        ) from exc

    if response.status_code >= 400:
        LOGGER.warning(
            "OIDC token exchange failed with status %s: %s",
            response.status_code,
            response.text[:500],
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falha na autenticacao.",
        )

    try:
        tokens = OIDCTokenResponse.model_validate(response.json())
    except ValidationError as exc:
        LOGGER.warning("OIDC token response was invalid: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Resposta de autenticacao invalida.",
        ) from exc

    LOGGER.info("OIDC id_token diagnostic: %s", _jwt_diagnostic(tokens.id_token))
    return tokens


async def verify_authentik_jwt(
    token: str,
    *,
    settings: Settings,
    expected_nonce: str | None = None,
) -> dict[str, Any]:
    metadata = await get_oidc_metadata(settings)
    jwks = await get_jwks(metadata, settings)

    try:
        signing_key = signing_key_from_jwks(token, jwks)
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=settings.authentik_algorithms,
            audience=settings.authentik_client_id,
            issuer=metadata.issuer,
            options={"require": ["aud", "exp", "iat", "iss", "sub"]},
        )
    except InvalidTokenError as exc:
        LOGGER.info(
            "Rejected invalid Authentik JWT: %s: %s; %s",
            exc.__class__.__name__,
            exc,
            _jwt_diagnostic(token),
        )
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
