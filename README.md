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
.\.venv\Scripts\alembic -x migration_scope=tenant -x tenant_schema=tenant_cliente_acme upgrade head
```

Depois do login, a primeira tela autenticada e `/app`. O dashboard geral fica em
`/app/dashboard`, e o modulo de empresas fica em
`/app/tenants/<tenant-id>/empresas`.

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

O Compose tambem sobe um PostgreSQL apenas na rede interna do Docker, sem
publicar a porta `5432` no host. A API acessa o banco por `db:5432`. A senha em
`POSTGRES_PASSWORD` precisa ser a mesma senha presente em `DATABASE_URL`. Se o
volume do Postgres ja tiver sido criado com outra senha, alterar o `.env` nao
troca a senha do banco existente.

Antes da API iniciar, o servico `migrate` executa as migracoes globais do
Alembic e cria as tabelas do schema `public`, incluindo `public.app_users`.
Se precisar rodar manualmente em um servidor ja criado:

```bash
cd docker
docker compose run --rm migrate
docker compose restart api
```

As migracoes de tenant precisam rodar para cada schema `tenant_*` existente,
especialmente quando houver alteracoes na tabela `companies`:

```bash
for schema in $(docker compose exec -T api python -m app.cli list-tenants | awk '{print $3}'); do
  docker compose run --rm migrate alembic -x migration_scope=tenant -x tenant_schema="$schema" upgrade head
done
docker compose restart api
```

Para um banco novo, sem dados a preservar, recrie o volume:

```bash
cd docker
docker compose down -v
docker compose up -d --build
```

Para preservar dados, altere a senha dentro do Postgres ou ajuste a
`DATABASE_URL` para a senha que ja existe no volume.

A API usa schemas separados por cliente: o schema `public` guarda tenants,
usuarios e permissoes; cada tenant recebe um schema proprio com a tabela
`companies`.
