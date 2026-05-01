from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .sanitization import sanitize_plain_text

CompanyStatus = Literal["active", "inactive"]
TaxRegime = Literal[
    "simples_nacional",
    "lucro_presumido",
    "lucro_real",
    "mei",
    "isento",
    "outro",
]


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


class CompanyListParams(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1, le=1000)
    page_size: int = Field(default=20, ge=1, le=100)
    q: str | None = Field(default=None, max_length=80)
    status: CompanyStatus | Literal["all"] = "active"

    @field_validator("q")
    @classmethod
    def sanitize_query(cls, value: str | None) -> str | None:
        if value is None:
            return None
        sanitized = sanitize_plain_text(value, max_length=80, allow_markup=False)
        return sanitized or None


class CompanyBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    legal_name: str = Field(min_length=2, max_length=180)
    trade_name: str | None = Field(default=None, max_length=180)
    tax_id: str = Field(min_length=3, max_length=32)
    tax_regime: TaxRegime | None = None
    state_registration: str | None = Field(default=None, max_length=40)
    municipal_registration: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    postal_code: str | None = Field(default=None, max_length=20)
    street: str | None = Field(default=None, max_length=160)
    number: str | None = Field(default=None, max_length=30)
    complement: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=2, min_length=2)
    country: str = Field(default="BR", min_length=2, max_length=2)

    @field_validator(
        "legal_name",
        "trade_name",
        "tax_id",
        "state_registration",
        "municipal_registration",
        "phone",
        "postal_code",
        "street",
        "number",
        "complement",
        "district",
        "city",
        "state",
        "country",
    )
    @classmethod
    def sanitize_company_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_plain_text(value, max_length=180, allow_markup=False)


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    legal_name: str | None = Field(default=None, min_length=2, max_length=180)
    trade_name: str | None = Field(default=None, max_length=180)
    tax_id: str | None = Field(default=None, min_length=3, max_length=32)
    tax_regime: TaxRegime | None = None
    state_registration: str | None = Field(default=None, max_length=40)
    municipal_registration: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    postal_code: str | None = Field(default=None, max_length=20)
    street: str | None = Field(default=None, max_length=160)
    number: str | None = Field(default=None, max_length=30)
    complement: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=2, min_length=2)
    country: str | None = Field(default=None, min_length=2, max_length=2)

    @field_validator(
        "legal_name",
        "trade_name",
        "tax_id",
        "state_registration",
        "municipal_registration",
        "phone",
        "postal_code",
        "street",
        "number",
        "complement",
        "district",
        "city",
        "state",
        "country",
    )
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
    status: CompanyStatus
    tax_regime: TaxRegime | None
    state_registration: str | None
    municipal_registration: str | None
    email: str | None
    phone: str | None
    postal_code: str | None
    street: str | None
    number: str | None
    complement: str | None
    district: str | None
    city: str | None
    state: str | None
    country: str
    created_at: datetime
    updated_at: datetime


class CompanyListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: list[CompanyRead]
    page: int
    page_size: int
    total: int
