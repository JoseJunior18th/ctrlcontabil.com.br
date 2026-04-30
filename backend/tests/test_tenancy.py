from __future__ import annotations

import pytest

from app.config import Settings
from app.database import quote_identifier
from app.models import AuthenticatedPrincipal
from app.tenancy import has_global_admin_role, schema_name_from_slug


def test_schema_name_from_slug_is_stable() -> None:
    assert schema_name_from_slug("cliente-acme") == "tenant_cliente_acme"


def test_quote_identifier_rejects_unsafe_schema_name() -> None:
    with pytest.raises(ValueError):
        quote_identifier('tenant_acme"; drop schema public; --')


def test_global_admin_roles_can_come_from_authentik_roles() -> None:
    settings = Settings(global_admin_roles=["owner"])
    principal = AuthenticatedPrincipal(sub="user-1", roles=("owner",))

    assert has_global_admin_role(principal, settings)


def test_global_admin_roles_can_come_from_authentik_groups() -> None:
    settings = Settings(global_admin_roles=["platform_owner"])
    principal = AuthenticatedPrincipal(sub="user-1", groups=("platform_owner",))

    assert has_global_admin_role(principal, settings)
