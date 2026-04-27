from typing import Literal

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
