from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from .config import get_settings
from .database import AsyncSessionLocal
from .db_models import AppUser, Tenant, TenantMembership
from .models import AuthenticatedPrincipal, TenantCreate
from .tenancy import create_tenant


async def provision_tenant(args: argparse.Namespace) -> None:
    settings = get_settings()
    principal = AuthenticatedPrincipal(
        sub=args.owner_sub,
        email=args.owner_email,
        name=args.owner_name,
        roles=("owner",),
    )
    payload = TenantCreate(
        slug=args.slug,
        display_name=args.name,
        initial_admin_auth_subject=args.admin_sub,
        initial_admin_email=args.admin_email,
        initial_admin_name=args.admin_name,
    )

    async with AsyncSessionLocal() as session:
        async with session.begin():
            tenant = await create_tenant(
                session,
                principal=principal,
                settings=settings,
                payload=payload,
            )
        print(f"Provisioned tenant {tenant.slug} in schema {tenant.schema_name}")


async def list_tenants(_args: argparse.Namespace) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Tenant).order_by(Tenant.display_name))
        for tenant in result.scalars():
            print(f"{tenant.id} {tenant.slug} {tenant.schema_name} {tenant.status}")


async def add_membership(args: argparse.Namespace) -> None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            tenant = (
                await session.execute(select(Tenant).where(Tenant.slug == args.tenant_slug))
            ).scalar_one()
            user = (
                await session.execute(select(AppUser).where(AppUser.auth_subject == args.user_sub))
            ).scalar_one_or_none()
            if user is None:
                user = AppUser(
                    auth_subject=args.user_sub,
                    email=args.user_email,
                    name=args.user_name,
                )
                session.add(user)
                await session.flush()
            session.add(
                TenantMembership(
                    tenant_id=tenant.id,
                    user_id=user.id,
                    role=args.role,
                    status="active",
                )
            )
        print(f"Added {args.user_sub} to {args.tenant_slug} as {args.role}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ctrl Contabil tenant administration")
    subparsers = parser.add_subparsers(dest="command", required=True)

    provision = subparsers.add_parser("provision-tenant")
    provision.add_argument("--slug", required=True)
    provision.add_argument("--name", required=True)
    provision.add_argument("--admin-sub", required=True)
    provision.add_argument("--admin-email")
    provision.add_argument("--admin-name")
    provision.add_argument("--owner-sub", default="cli-owner")
    provision.add_argument("--owner-email")
    provision.add_argument("--owner-name", default="CLI Owner")
    provision.set_defaults(func=provision_tenant)

    list_cmd = subparsers.add_parser("list-tenants")
    list_cmd.set_defaults(func=list_tenants)

    membership = subparsers.add_parser("add-membership")
    membership.add_argument("--tenant-slug", required=True)
    membership.add_argument("--user-sub", required=True)
    membership.add_argument("--user-email")
    membership.add_argument("--user-name")
    membership.add_argument("--role", choices=["admin", "member", "viewer"], default="member")
    membership.set_defaults(func=add_membership)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()
