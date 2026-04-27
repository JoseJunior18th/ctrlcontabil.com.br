from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import PlainTextResponse, RedirectResponse

from .config import Settings, get_settings
from .models import AuthenticatedPrincipal
from .security import (
    issue_session_token,
    normalize_string_claims,
    safe_redirect_target,
    set_session_cookie,
)

try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth  # type: ignore[import-not-found]
    from onelogin.saml2.settings import OneLogin_Saml2_Settings  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - optional deployment extra
    OneLogin_Saml2_Auth = None
    OneLogin_Saml2_Settings = None


router = APIRouter(prefix="/saml", tags=["saml"])


def _require_saml() -> None:
    if OneLogin_Saml2_Auth is None or OneLogin_Saml2_Settings is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SAML nao esta instalado neste deploy.",
        )


def _require_saml_config(settings: Settings) -> None:
    if settings.saml_idp_x509_cert is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SAML nao esta configurado neste deploy.",
        )


def _saml_settings(settings: Settings) -> dict[str, Any]:
    idp_entity_id = settings.saml_idp_entity_id or settings.authentik_issuer.rstrip("/")
    idp_sso_url = (
        settings.saml_idp_sso_url
        or f"{settings.authentik_issuer.rstrip('/')}/sso/binding/redirect/"
    )
    idp_slo_url = (
        settings.saml_idp_slo_url
        or f"{settings.authentik_issuer.rstrip('/')}/slo/binding/redirect/"
    )
    sign_sp_requests = bool(settings.saml_sp_x509_cert and settings.saml_sp_private_key)

    return {
        "strict": True,
        "debug": settings.environment != "production",
        "sp": {
            "entityId": f"{settings.api_base_url.rstrip('/')}/saml/metadata",
            "assertionConsumerService": {
                "url": f"{settings.api_base_url.rstrip('/')}/saml/acs",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "singleLogoutService": {
                "url": f"{settings.api_base_url.rstrip('/')}/saml/sls",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            "x509cert": (
                settings.saml_sp_x509_cert.get_secret_value()
                if settings.saml_sp_x509_cert
                else ""
            ),
            "privateKey": (
                settings.saml_sp_private_key.get_secret_value()
                if settings.saml_sp_private_key
                else ""
            ),
        },
        "idp": {
            "entityId": idp_entity_id,
            "singleSignOnService": {
                "url": idp_sso_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "singleLogoutService": {
                "url": idp_slo_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": settings.saml_idp_x509_cert.get_secret_value()
            if settings.saml_idp_x509_cert
            else "",
        },
        "security": {
            "authnRequestsSigned": sign_sp_requests,
            "logoutRequestSigned": sign_sp_requests,
            "logoutResponseSigned": sign_sp_requests,
            "wantAssertionsSigned": True,
            "wantMessagesSigned": True,
            "wantNameIdEncrypted": False,
            "wantAssertionsEncrypted": False,
            "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
            "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
        },
    }


async def _request_data(request: Request) -> dict[str, Any]:
    form = await request.form()
    url = request.url
    return {
        "https": "on" if url.scheme == "https" else "off",
        "http_host": request.headers.get("host", ""),
        "script_name": request.url.path,
        "server_port": str(url.port or (443 if url.scheme == "https" else 80)),
        "get_data": dict(request.query_params),
        "post_data": dict(form),
    }


async def _auth(request: Request, settings: Settings) -> Any:
    _require_saml()
    _require_saml_config(settings)
    return OneLogin_Saml2_Auth(await _request_data(request), old_settings=_saml_settings(settings))


@router.get("/metadata")
async def metadata() -> PlainTextResponse:
    settings = get_settings()
    _require_saml()
    _require_saml_config(settings)
    saml_settings = OneLogin_Saml2_Settings(_saml_settings(settings), sp_validation_only=True)
    metadata_xml = saml_settings.get_sp_metadata()
    errors = saml_settings.validate_metadata(metadata_xml)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Metadata invalido.",
        )
    return PlainTextResponse(metadata_xml, media_type="application/samlmetadata+xml")


@router.get("/login")
async def saml_login(request: Request, return_to: str | None = None) -> RedirectResponse:
    settings = get_settings()
    auth = await _auth(request, settings)
    target = safe_redirect_target(return_to, settings)
    return RedirectResponse(auth.login(return_to=target))


@router.post("/acs")
async def saml_acs(request: Request) -> RedirectResponse:
    settings = get_settings()
    auth = await _auth(request, settings)
    auth.process_response()

    if auth.get_errors() or not auth.is_authenticated():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="SAML invalido.")

    attributes = auth.get_attributes()
    name_id = auth.get_nameid()
    principal = AuthenticatedPrincipal(
        sub=name_id,
        email=(attributes.get("email") or [None])[0],
        groups=normalize_string_claims(attributes.get("groups")),
        name=(attributes.get("name") or [None])[0],
        preferred_username=(attributes.get("username") or [None])[0],
        roles=normalize_string_claims(attributes.get("roles")),
        sid=auth.get_session_index(),
    )

    relay_state = (await request.form()).get("RelayState")
    target = safe_redirect_target(str(relay_state) if relay_state else None, settings)
    response = RedirectResponse(target)
    set_session_cookie(response, issue_session_token(principal, settings), settings)
    return response


@router.get("/sls")
async def saml_sls(request: Request) -> RedirectResponse:
    settings = get_settings()
    auth = await _auth(request, settings)
    url = auth.process_slo(delete_session_cb=lambda: None)
    if auth.get_errors():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logout SAML invalido.")
    return RedirectResponse(url or settings.frontend_base_url)
