from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parent.parent))

    from app.config import get_settings
    from app.models import (
        AuthenticatedPrincipal,
        DocumentCreate,
        DocumentSearchParams,
        PublicUser,
        SessionPayload,
    )
    from app.oidc import (
        OIDCState,
        build_authorization_url,
        decode_oidc_state_cookie,
        end_session_url,
        exchange_authorization_code,
        get_oidc_metadata,
        issue_oidc_state_cookie,
        principal_from_claims,
        verify_authentik_jwt,
    )
    from app.saml import router as saml_router
    from app.security import (
        InMemoryRateLimiter,
        clear_session_cookie,
        issue_session_token,
        new_token_urlsafe,
        principal_from_session_token,
        rate_limit_key,
        safe_redirect_target,
        set_session_cookie,
    )
else:
    from .config import get_settings
    from .models import (
        AuthenticatedPrincipal,
        DocumentCreate,
        DocumentSearchParams,
        PublicUser,
        SessionPayload,
    )
    from .oidc import (
        OIDCState,
        build_authorization_url,
        decode_oidc_state_cookie,
        end_session_url,
        exchange_authorization_code,
        get_oidc_metadata,
        issue_oidc_state_cookie,
        principal_from_claims,
        verify_authentik_jwt,
    )
    from .saml import router as saml_router
    from .security import (
        InMemoryRateLimiter,
        clear_session_cookie,
        issue_session_token,
        new_token_urlsafe,
        principal_from_session_token,
        rate_limit_key,
        safe_redirect_target,
        set_session_cookie,
    )

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

settings = get_settings()
rate_limiter = InMemoryRateLimiter(
    max_requests=settings.rate_limit_max_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
revoked_sids: dict[str, int] = {}


def auth_error_redirect(reason: str) -> RedirectResponse:
    params = urlencode({"reason": reason})
    return RedirectResponse(f"{settings.frontend_base_url.rstrip('/')}/auth/error?{params}")

app = FastAPI(
    title=settings.app_name,
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc",
)

if settings.enable_https_redirect:
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_origins=settings.allowed_origins,
)
app.include_router(saml_router)


@app.middleware("http")
async def security_boundary(request: Request, call_next):  # type: ignore[no-untyped-def]
    if request.url.path != "/healthz":
        retry_after = rate_limiter.check(rate_limit_key(request))
        if retry_after is not None:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Muitas requisicoes. Tente novamente em instantes."},
                headers={"Retry-After": str(retry_after)},
            )

    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    LOGGER.info("Validation rejected at %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Payload invalido.", "code": "VALIDATION_ERROR"},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    LOGGER.info("HTTP error at %s: %s", request.url.path, exc.status_code)
    safe_messages = {
        status.HTTP_400_BAD_REQUEST: "Requisicao invalida.",
        status.HTTP_401_UNAUTHORIZED: "Nao autenticado.",
        status.HTTP_403_FORBIDDEN: "Acesso negado.",
        status.HTTP_404_NOT_FOUND: "Recurso nao encontrado.",
        status.HTTP_429_TOO_MANY_REQUESTS: "Muitas requisicoes.",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": safe_messages.get(exc.status_code, "Nao foi possivel processar.")},
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    LOGGER.exception("Unhandled error at %s", request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno."},
    )


def _is_revoked(principal: AuthenticatedPrincipal) -> bool:
    now = int(time.time())
    if principal.sid and revoked_sids.get(principal.sid, 0) > now:
        return True
    return False


async def current_principal(request: Request) -> AuthenticatedPrincipal:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        claims = await verify_authentik_jwt(token, settings=settings)
        principal = principal_from_claims(claims)
    else:
        session_token = request.cookies.get(settings.session_cookie_name)
        if not session_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nao autenticado.")
        principal = principal_from_session_token(session_token, settings)

    if _is_revoked(principal):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao revogada.")

    return principal


PrincipalDep = Annotated[AuthenticatedPrincipal, Depends(current_principal)]


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/auth/login")
async def login(
    return_to: Annotated[str | None, Query(max_length=2048)] = None,
) -> RedirectResponse:
    metadata = await get_oidc_metadata(settings)
    oidc_state = OIDCState(
        code_verifier=new_token_urlsafe(64),
        nonce=new_token_urlsafe(32),
        return_to=safe_redirect_target(return_to, settings),
        state=new_token_urlsafe(32),
    )
    state_cookie = issue_oidc_state_cookie(oidc_state, settings)
    response = RedirectResponse(build_authorization_url(metadata, oidc_state, settings))
    response.set_cookie(
        key=settings.auth_state_cookie_name,
        value=state_cookie,
        max_age=settings.auth_state_ttl_seconds,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
        domain=settings.session_cookie_domain,
    )
    return response


@app.get("/auth/callback")
async def callback(
    request: Request,
    code: Annotated[str | None, Query(max_length=4096)] = None,
    state: Annotated[str | None, Query(max_length=256)] = None,
    error: Annotated[str | None, Query(max_length=120)] = None,
) -> RedirectResponse:
    if error:
        LOGGER.warning("OIDC provider returned error during callback: %s", error)
        reason = "provider_denied" if error == "access_denied" else "provider_error"
        return auth_error_redirect(reason)

    if not code or not state:
        LOGGER.warning("OIDC callback missing code or state.")
        return auth_error_redirect("missing_callback_params")

    state_cookie = request.cookies.get(settings.auth_state_cookie_name)
    if not state_cookie:
        LOGGER.warning("OIDC callback received without state cookie.")
        return auth_error_redirect("missing_state_cookie")

    try:
        oidc_state = decode_oidc_state_cookie(state_cookie, settings)
    except HTTPException:
        LOGGER.warning("OIDC callback received an invalid state cookie.")
        return auth_error_redirect("invalid_state_cookie")

    if oidc_state.state != state:
        LOGGER.warning("OIDC callback state mismatch.")
        return auth_error_redirect("state_mismatch")

    metadata = await get_oidc_metadata(settings)
    try:
        tokens = await exchange_authorization_code(
            code=code,
            metadata=metadata,
            oidc_state=oidc_state,
            settings=settings,
        )
        claims = await verify_authentik_jwt(
            tokens.id_token,
            settings=settings,
            expected_nonce=oidc_state.nonce,
        )
    except HTTPException as exc:
        LOGGER.warning("OIDC callback failed after provider redirect: %s", exc.status_code)
        return auth_error_redirect("token_validation_failed")

    principal = principal_from_claims(claims)
    session_token = issue_session_token(principal, settings)

    response = RedirectResponse(oidc_state.return_to)
    set_session_cookie(response, session_token, settings)
    response.delete_cookie(
        key=settings.auth_state_cookie_name,
        path="/",
        domain=settings.session_cookie_domain,
    )
    return response


@app.get("/auth/session", response_model=SessionPayload)
async def session(principal: PrincipalDep) -> SessionPayload:
    return SessionPayload(user=PublicUser.from_principal(principal))


@app.get("/auth/logout")
async def logout(
    return_to: Annotated[str | None, Query(max_length=2048)] = None,
) -> RedirectResponse:
    target = safe_redirect_target(return_to or "/", settings)
    redirect_target = await end_session_url(settings, target)
    response = RedirectResponse(redirect_target)
    clear_session_cookie(response, settings)
    return response


@app.post("/auth/backchannel-logout", status_code=status.HTTP_204_NO_CONTENT)
async def backchannel_logout(logout_token: Annotated[str, Form(max_length=8192)]) -> Response:
    claims = await verify_authentik_jwt(logout_token, settings=settings)
    events = claims.get("events")
    backchannel_event = "http://schemas.openid.net/event/backchannel-logout"
    if not isinstance(events, dict) or backchannel_event not in events:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logout invalido.")

    ttl_until = int(time.time()) + settings.session_ttl_seconds
    sid = claims.get("sid")
    if isinstance(sid, str):
        revoked_sids[sid] = ttl_until

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/profile", response_model=PublicUser)
async def profile(principal: PrincipalDep) -> PublicUser:
    return PublicUser.from_principal(principal)


@app.get("/api/documents")
async def search_documents(
    principal: PrincipalDep,
    params: Annotated[DocumentSearchParams, Depends()],
) -> dict[str, object]:
    return {
        "items": [],
        "page": params.page,
        "page_size": params.page_size,
        "query": params.q,
        "requested_by": principal.sub,
    }


@app.post("/api/documents", status_code=status.HTTP_202_ACCEPTED)
async def create_document(
    principal: PrincipalDep,
    payload: DocumentCreate,
) -> dict[str, str]:
    LOGGER.info(
        "Accepted document request from sub=%s type=%s",
        principal.sub,
        payload.document_type,
    )
    return {"status": "accepted"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=5075, reload=True)
