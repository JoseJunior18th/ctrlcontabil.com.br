# Ctrl Contabil Backend

FastAPI backend for production authentication and API boundaries.

## Local run

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -e ".[test]"
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

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
https://ctrlcontabil.josejunior.eng.br/        -> Next.js on 127.0.0.1:8232
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
