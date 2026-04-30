from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .sanitization import sanitize_plain_text


class AuthenticatedPrincipal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    sub: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    groups: tuple[str, ...] = ()
    name: str | None = Field(default=None, max_length=120)
    preferred_username: str | None = Field(default=None, max_length=80)
    roles: tuple[str, ...] = ()
    sid: str | None = Field(default=None, max_length=255)


class PublicUser(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sub: str
    email: str | None
    groups: list[str]
    name: str | None
    preferredUsername: str | None
    roles: list[str]

    @classmethod
    def from_principal(cls, principal: AuthenticatedPrincipal) -> "PublicUser":
        return cls(
            sub=principal.sub,
            email=str(principal.email) if principal.email else None,
            groups=list(principal.groups),
            name=principal.name,
            preferredUsername=principal.preferred_username,
            roles=list(principal.roles),
        )


class SessionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    authenticated: Literal[True] = True
    user: PublicUser


class DocumentSearchParams(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1, le=100)
    page_size: int = Field(default=20, ge=1, le=100)
    q: str | None = Field(default=None, max_length=80)

    @field_validator("q")
    @classmethod
    def sanitize_query(cls, value: str | None) -> str | None:
        if value is None:
            return None
        sanitized = sanitize_plain_text(value, max_length=80, allow_markup=False)
        return sanitized or None


class DocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)

    amount_cents: int = Field(ge=0, le=1_000_000_000)
    document_type: Literal["darf", "nfe", "recibo", "outro"]
    reference: str | None = Field(default=None, max_length=80)
    title: str = Field(min_length=1, max_length=120)

    @field_validator("reference", "title")
    @classmethod
    def sanitize_text_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_plain_text(value, max_length=120, allow_markup=False)


class TenantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    display_name: str = Field(min_length=2, max_length=160)
    initial_admin_auth_subject: str | None = Field(default=None, min_length=1, max_length=255)
    initial_admin_email: EmailStr | None = None
    initial_admin_name: str | None = Field(default=None, max_length=120)

    @field_validator("display_name", "initial_admin_name")
    @classmethod
    def sanitize_name_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_plain_text(value, max_length=160, allow_markup=False)


class TenantRead(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    slug: str
    display_name: str
    status: str
    created_at: datetime
    updated_at: datetime


class CompanyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    legal_name: str = Field(min_length=2, max_length=180)
    trade_name: str | None = Field(default=None, max_length=180)
    tax_id: str = Field(min_length=3, max_length=32)

    @field_validator("legal_name", "trade_name", "tax_id")
    @classmethod
    def sanitize_company_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_plain_text(value, max_length=180, allow_markup=False)


class CompanyRead(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    legal_name: str
    trade_name: str | None
    tax_id: str
    status: str
    created_at: datetime
    updated_at: datetime
