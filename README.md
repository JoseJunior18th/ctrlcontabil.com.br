# Ctrl Contabil

## Estrutura

```text
docker/              Dockerfiles, Compose e exemplo de variaveis
infra/nginx/         Configuracao Nginx de producao
web/                 Aplicacao Next.js
backend/             API FastAPI
```

Host inicial de producao:

```text
https://ctrlcontabil.josejunior.eng.br
```

Callback OIDC no Authentik:

```text
https://ctrlcontabil.josejunior.eng.br/auth/callback
```

Issuer OIDC esperado:

```text
https://authentik.onneonline.com.br/application/o/ctrlcontabil/
```

## Desenvolvimento

Frontend:

```powershell
cd web
npm install
npm run dev
```

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -e ".[test]"
.\.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 5075
```

Migrações e tenant inicial:

```powershell
cd backend
.\.venv\Scripts\alembic -x migration_scope=global upgrade head
.\.venv\Scripts\python -m app.cli provision-tenant --slug cliente-acme --name "Cliente ACME" --admin-sub "<sub-authentik>"
```

## Deploy com Docker

Use `docker/.env` para os valores reais de producao. O modelo fica em
`docker/env.example`. Esse arquivo e usado apenas pelo Docker Compose para
interpolar o bloco `environment:` dos servicos; ele nao e copiado para a imagem
nem precisa existir dentro de `web/` ou `backend/`.

```bash
cp docker/env.example docker/.env
docker compose --env-file docker/.env -f docker/docker-compose.yml up -d --build
```

O Compose publica o Next em `127.0.0.1:8230` e a API em `127.0.0.1:5075`.
O Nginx em `infra/nginx/ctrlcontabil.josejunior.eng.br.conf` faz o roteamento
same-origin para preservar o cookie `__Host-ctrl_session`.

O Compose tambem sobe um PostgreSQL em `127.0.0.1:5432`. A API usa schemas
separados por cliente: o schema `public` guarda tenants, usuarios e permissoes;
cada tenant recebe um schema proprio com a tabela `companies`.
