from __future__ import annotations

import re
import uuid

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings
from .database import quote_identifier, set_tenant_search_path
from .db_models import AppUser, AuditEvent, Company, Tenant, TenantMembership
from .models import (
    AuthenticatedPrincipal,
    CompanyCreate,
    CompanyListParams,
    CompanyUpdate,
    TenantCreate,
)

GLOBAL_ADMIN_ROLES = {"owner", "admin", "platform_owner"}
TENANT_SCHEMA_PREFIX = "tenant_"
SLUG_RE = re.compile(r"[^a-z0-9]+")


def has_global_admin_role(principal: AuthenticatedPrincipal, settings: Settings) -> bool:
    configured_roles = {role.lower() for role in settings.global_admin_roles} or GLOBAL_ADMIN_ROLES
    principal_roles = {role.lower() for role in principal.roles}
    principal_roles.update(group.lower() for group in principal.groups)
    return bool(configured_roles.intersection(principal_roles))


def schema_name_from_slug(slug: str) -> str:
    normalized = SLUG_RE.sub("_", slug.lower()).strip("_")
    schema_name = f"{TENANT_SCHEMA_PREFIX}{normalized}"
    return schema_name[:63]


async def upsert_app_user(
    session: AsyncSession,
    principal: AuthenticatedPrincipal,
    settings: Settings,
) -> AppUser:
    result = await session.execute(
        select(AppUser).where(AppUser.auth_subject == principal.sub)
    )
    app_user = result.scalar_one_or_none()
    is_global_admin = has_global_admin_role(principal, settings)

    if app_user is None:
        app_user = AppUser(
            auth_subject=principal.sub,
            email=str(principal.email) if principal.email else None,
            name=principal.name,
            is_global_admin=is_global_admin,
        )
        session.add(app_user)
    else:
        app_user.email = str(principal.email) if principal.email else app_user.email
        app_user.name = principal.name or app_user.name
        app_user.is_global_admin = app_user.is_global_admin or is_global_admin

    await session.flush()
    return app_user


async def ensure_global_admin(
    session: AsyncSession,
    principal: AuthenticatedPrincipal,
    settings: Settings,
) -> AppUser:
    app_user = await upsert_app_user(session, principal, settings)
    if not app_user.is_global_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado.")
    return app_user


async def list_accessible_tenants(
    session: AsyncSession,
    principal: AuthenticatedPrincipal,
    settings: Settings,
) -> list[Tenant]:
    app_user = await upsert_app_user(session, principal, settings)

    if app_user.is_global_admin:
        statement: Select[tuple[Tenant]] = (
            select(Tenant)
            .where(Tenant.status == "active")
            .order_by(Tenant.display_name)
        )
    else:
        statement = (
            select(Tenant)
            .join(TenantMembership, TenantMembership.tenant_id == Tenant.id)
            .where(
                Tenant.status == "active",
                TenantMembership.user_id == app_user.id,
                TenantMembership.status == "active",
            )
            .order_by(Tenant.display_name)
        )

    result = await session.execute(statement)
    return list(result.scalars().all())


async def resolve_tenant_access(
    session: AsyncSession,
    principal: AuthenticatedPrincipal,
    settings: Settings,
    tenant_id: uuid.UUID,
) -> tuple[Tenant, AppUser]:
    app_user = await upsert_app_user(session, principal, settings)
    result = await session.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.status == "active")
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso nao encontrado.")

    if app_user.is_global_admin:
        return tenant, app_user

    membership_result = await session.execute(
        select(TenantMembership.id).where(
            TenantMembership.tenant_id == tenant.id,
            TenantMembership.user_id == app_user.id,
            TenantMembership.status == "active",
        )
    )
    if membership_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado.")

    return tenant, app_user


async def create_audit_event(
    session: AsyncSession,
    *,
    actor_user_id: uuid.UUID | None,
    tenant_id: uuid.UUID | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    session.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            tenant_id=tenant_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            event_metadata=metadata or {},
        )
    )


async def create_tenant_schema(session: AsyncSession, schema_name: str) -> None:
    quoted_schema = quote_identifier(schema_name)
    await session.execute(text(f"CREATE SCHEMA {quoted_schema}"))
    await session.execute(
        text(
            f"""
            CREATE TABLE {quoted_schema}.companies (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                legal_name varchar(180) NOT NULL,
                trade_name varchar(180),
                tax_id varchar(32) NOT NULL,
                status varchar(20) NOT NULL DEFAULT 'active',
                tax_regime varchar(40),
                state_registration varchar(40),
                municipal_registration varchar(40),
                email varchar(255),
                phone varchar(40),
                postal_code varchar(20),
                street varchar(160),
                number varchar(30),
                complement varchar(120),
                district varchar(120),
                city varchar(120),
                state varchar(2),
                country varchar(2) NOT NULL DEFAULT 'BR',
                created_by_user_id uuid NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT uq_companies_tax_id UNIQUE (tax_id),
                CONSTRAINT ck_companies_status CHECK (status IN ('active', 'inactive')),
                CONSTRAINT ck_companies_tax_regime CHECK (
                    tax_regime IS NULL OR tax_regime IN (
                        'simples_nacional',
                        'lucro_presumido',
                        'lucro_real',
                        'mei',
                        'isento',
                        'outro'
                    )
                )
            )
            """
        )
    )


async def create_tenant(
    session: AsyncSession,
    *,
    principal: AuthenticatedPrincipal,
    settings: Settings,
    payload: TenantCreate,
) -> Tenant:
    actor = await ensure_global_admin(session, principal, settings)
    schema_name = schema_name_from_slug(payload.slug)
    quote_identifier(schema_name)

    existing = await session.execute(
        select(Tenant.id).where(
            (Tenant.slug == payload.slug) | (Tenant.schema_name == schema_name)
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant ja existe.")

    await session.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    tenant = Tenant(
        slug=payload.slug,
        display_name=payload.display_name,
        schema_name=schema_name,
    )
    session.add(tenant)
    await session.flush()

    admin_subject = payload.initial_admin_auth_subject or principal.sub
    admin_user = await get_or_create_admin_user(session, payload, admin_subject, principal)
    session.add(
        TenantMembership(
            tenant_id=tenant.id,
            user_id=admin_user.id,
            role="admin",
            status="active",
        )
    )

    await create_tenant_schema(session, schema_name)
    await create_audit_event(
        session,
        actor_user_id=actor.id,
        tenant_id=tenant.id,
        action="tenant.created",
        entity_type="tenant",
        entity_id=str(tenant.id),
        metadata={"schema_name": schema_name},
    )
    return tenant


async def get_or_create_admin_user(
    session: AsyncSession,
    payload: TenantCreate,
    admin_subject: str,
    principal: AuthenticatedPrincipal,
) -> AppUser:
    result = await session.execute(
        select(AppUser).where(AppUser.auth_subject == admin_subject)
    )
    app_user = result.scalar_one_or_none()
    if app_user is not None:
        return app_user

    app_user = AppUser(
        auth_subject=admin_subject,
        email=str(payload.initial_admin_email) if payload.initial_admin_email else None,
        name=payload.initial_admin_name or principal.name,
    )
    session.add(app_user)
    await session.flush()
    return app_user


async def list_companies(
    session: AsyncSession,
    *,
    tenant: Tenant,
    params: CompanyListParams,
) -> tuple[list[Company], int]:
    await set_tenant_search_path(session, tenant.schema_name)
    conditions = []
    if params.status != "all":
        conditions.append(Company.status == params.status)
    if params.q:
        query = f"%{params.q}%"
        conditions.append(
            or_(
                Company.legal_name.ilike(query),
                Company.trade_name.ilike(query),
                Company.tax_id.ilike(query),
                Company.email.ilike(query),
            )
        )

    count_statement = select(func.count()).select_from(Company)
    list_statement = select(Company).order_by(Company.legal_name, Company.created_at.desc())
    if conditions:
        count_statement = count_statement.where(*conditions)
        list_statement = list_statement.where(*conditions)

    total = (await session.execute(count_statement)).scalar_one()
    offset = (params.page - 1) * params.page_size
    result = await session.execute(list_statement.offset(offset).limit(params.page_size))
    return list(result.scalars().all()), total


async def get_company(
    session: AsyncSession,
    *,
    tenant: Tenant,
    company_id: uuid.UUID,
) -> Company:
    await set_tenant_search_path(session, tenant.schema_name)
    result = await session.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso nao encontrado.")
    return company


async def create_company(
    session: AsyncSession,
    *,
    tenant: Tenant,
    app_user: AppUser,
    payload: CompanyCreate,
) -> Company:
    await set_tenant_search_path(session, tenant.schema_name)
    company = Company(
        legal_name=payload.legal_name,
        trade_name=payload.trade_name,
        tax_id=payload.tax_id,
        tax_regime=payload.tax_regime,
        state_registration=payload.state_registration,
        municipal_registration=payload.municipal_registration,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
        postal_code=payload.postal_code,
        street=payload.street,
        number=payload.number,
        complement=payload.complement,
        district=payload.district,
        city=payload.city,
        state=payload.state,
        country=payload.country,
        created_by_user_id=app_user.id,
    )
    session.add(company)
    await session.flush()
    await create_audit_event(
        session,
        actor_user_id=app_user.id,
        tenant_id=tenant.id,
        action="company.created",
        entity_type="company",
        entity_id=str(company.id),
    )
    return company


async def update_company(
    session: AsyncSession,
    *,
    tenant: Tenant,
    app_user: AppUser,
    company_id: uuid.UUID,
    payload: CompanyUpdate,
) -> Company:
    company = await get_company(session, tenant=tenant, company_id=company_id)
    changes = payload.model_dump(exclude_unset=True)
    if "email" in changes and changes["email"] is not None:
        changes["email"] = str(changes["email"])

    for field_name, value in changes.items():
        setattr(company, field_name, value)

    await session.flush()
    await create_audit_event(
        session,
        actor_user_id=app_user.id,
        tenant_id=tenant.id,
        action="company.updated",
        entity_type="company",
        entity_id=str(company.id),
        metadata={"fields": sorted(changes)},
    )
    return company


async def set_company_status(
    session: AsyncSession,
    *,
    tenant: Tenant,
    app_user: AppUser,
    company_id: uuid.UUID,
    status_value: str,
) -> Company:
    company = await get_company(session, tenant=tenant, company_id=company_id)
    company.status = status_value
    await session.flush()
    audit_action = "company.deactivated" if status_value == "inactive" else "company.reactivated"
    await create_audit_event(
        session,
        actor_user_id=app_user.id,
        tenant_id=tenant.id,
        action=audit_action,
        entity_type="company",
        entity_id=str(company.id),
    )
    return company
