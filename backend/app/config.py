from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


def _parse_csv(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item.strip() for item in value if item.strip()]
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Ctrl Contabil API"
    environment: Literal["development", "staging", "production", "test"] = "development"
    api_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:3000"

    authentik_issuer: str = "https://authentik.onneonline.com.br/application/o/ctrlcontabil/"
    authentik_client_id: str = "ctrlcontabil"
    authentik_client_secret: SecretStr = SecretStr("dev-only-change-me")
    authentik_algorithms: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["RS256"]
    )
    oidc_scopes: str = "openid profile email"

    saml_idp_entity_id: str | None = None
    saml_idp_sso_url: str | None = None
    saml_idp_slo_url: str | None = None
    saml_idp_x509_cert: SecretStr | None = None
    saml_sp_x509_cert: SecretStr | None = None
    saml_sp_private_key: SecretStr | None = None

    session_secret: SecretStr = SecretStr("dev-only-change-me-change-me-32-chars")
    session_cookie_name: str = "__Host-ctrl_session"
    session_cookie_domain: str | None = None
    session_ttl_seconds: int = Field(default=3600, ge=300, le=28800)
    secure_cookies: bool = True

    auth_state_cookie_name: str = "__Host-ctrl_oidc_state"
    auth_state_ttl_seconds: int = Field(default=600, ge=60, le=1800)

    allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    allowed_return_hosts: Annotated[list[str], NoDecode] = Field(default_factory=list)
    trusted_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "localhost",
            "127.0.0.1",
            "api",
            "testserver",
            "ctrlcontabil.josejunior.eng.br",
        ]
    )

    enable_https_redirect: bool = False
    request_timeout_seconds: float = Field(default=10.0, gt=0, le=30)
    rate_limit_max_requests: int = Field(default=60, ge=1, le=1000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)

    @field_validator(
        "allowed_origins",
        "allowed_return_hosts",
        "trusted_hosts",
        "authentik_algorithms",
        mode="before",
    )
    @classmethod
    def parse_csv_fields(cls, value: str | list[str] | None) -> list[str]:
        return _parse_csv(value)

    @model_validator(mode="after")
    def validate_security_defaults(self) -> "Settings":
        frontend_host = urlparse(self.frontend_base_url).hostname
        if frontend_host and not self.allowed_return_hosts:
            self.allowed_return_hosts = [frontend_host]

        if not self.allowed_origins:
            self.allowed_origins = [self.frontend_base_url.rstrip("/")]

        if self.session_cookie_name.startswith("__Host-"):
            if self.session_cookie_domain is not None:
                raise ValueError("__Host- cookies cannot define a Domain attribute.")
            if not self.secure_cookies:
                raise ValueError("__Host- cookies require Secure=true.")

        if self.environment == "production":
            self._require_https("api_base_url", self.api_base_url)
            self._require_https("frontend_base_url", self.frontend_base_url)
            self._require_https("authentik_issuer", self.authentik_issuer)

            if "dev-only" in self.session_secret.get_secret_value():
                raise ValueError("SESSION_SECRET must be changed before production.")
            if "dev-only" in self.authentik_client_secret.get_secret_value():
                raise ValueError("AUTHENTIK_CLIENT_SECRET must be changed before production.")
            if not self.enable_https_redirect:
                raise ValueError("ENABLE_HTTPS_REDIRECT must be true in production.")

        return self

    @staticmethod
    def _require_https(field_name: str, value: str) -> None:
        parsed = urlparse(value)
        if parsed.scheme != "https":
            raise ValueError(f"{field_name} must use HTTPS in production.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
