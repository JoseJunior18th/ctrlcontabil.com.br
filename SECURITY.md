# Security Review

## Critical findings fixed

- The dashboard was publicly reachable. Route access now fails closed through
  `middleware.ts` and `app/dashboard/page.tsx`, both validating the session at
  the Python API boundary.
- The login form collected credentials in the browser without a real backend
  authentication flow. It now delegates authentication to Authentik through OIDC.
- There was no server-side JWT validation. The FastAPI backend validates
  Authentik JWTs through issuer, audience, expiration and JWKS signature checks.
- There was no input validation or API boundary. New Pydantic models reject
  unknown fields, enforce size/range constraints and sanitize plain-text fields.
- There was no rate limiting. The backend now applies a conservative per-IP,
  per-route in-memory limiter. Use Redis or an API gateway limiter for
  multi-instance production.
- Errors could have leaked implementation detail once APIs were added. FastAPI
  exception handlers now return generic messages and log details server-side.
- Security headers were missing. Next and FastAPI now set CSP, frame denial,
  MIME sniffing protection, referrer policy and permission restrictions.

## Production notes

- Prefer OIDC over SAML unless a legacy system requires SAML. OIDC is implemented
  as the default. SAML route scaffolding exists under `backend/app/saml.py` and
  requires the optional backend extra `.[saml]` plus Authentik SAML certificate
  configuration before use.
- The safest cookie layout is a same-origin reverse proxy:
  `https://ctrlcontabil.josejunior.eng.br/auth/*` -> FastAPI and the Next app on
  the same host. That allows the `__Host-ctrl_session` cookie.
- If the API must live on `api.josejunior.eng.br`, do not use `__Host-` cookies.
  Configure `SESSION_COOKIE_NAME=ctrl_session` and
  `SESSION_COOKIE_DOMAIN=.josejunior.eng.br`.
- Keep Authentik JWTs asymmetrically signed. If no signing key is selected,
  Authentik can use the client secret for symmetric signing; this project is
  configured for JWKS/asymmetric validation.
- Replace the in-memory logout and rate-limit stores with Redis before running
  multiple backend replicas.
