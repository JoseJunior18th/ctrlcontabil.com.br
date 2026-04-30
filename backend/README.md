# Ctrl Contabil Backend

FastAPI backend for production authentication and API boundaries.

## Local run

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -e ".[test]"
.\.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 5075
```

## Database

The backend uses PostgreSQL with one catalog schema plus isolated tenant schemas.
Run global migrations first:

```powershell
.\.venv\Scripts\alembic -x migration_scope=global upgrade head
```

Provision a tenant and its first admin membership:

```powershell
.\.venv\Scripts\python -m app.cli provision-tenant --slug cliente-acme --name "Cliente ACME" --admin-sub "<authentik-sub>"
```

Tenant provisioning creates `public.tenants`, `public.app_users`,
`public.tenant_memberships`, the tenant schema and its `companies` table.

## Authentik OIDC

Create an Authentik OAuth2/OIDC application and set the redirect URI to:

```text
https://ctrlcontabil.josejunior.eng.br/auth/callback
```

The expected discovery URL is:

```text
https://authentik.onneonline.com.br/application/o/ctrlcontabil/.well-known/openid-configuration
```

Use a signing key in Authentik so JWTs are validated through JWKS with asymmetric
algorithms such as RS256.

For the first production deployment, prefer a same-origin reverse proxy:

```text
https://ctrlcontabil.josejunior.eng.br/        -> Next.js on 127.0.0.1:8230
https://ctrlcontabil.josejunior.eng.br/auth/*  -> FastAPI on 127.0.0.1:5075
https://ctrlcontabil.josejunior.eng.br/api/*   -> FastAPI on 127.0.0.1:5075
```

That layout keeps the `__Host-ctrl_session` cookie valid and avoids cross-site
cookie complexity.

The repository includes this deployment shape in:

```text
../docker/docker-compose.yml
../infra/nginx/ctrlcontabil.josejunior.eng.br.conf
```
