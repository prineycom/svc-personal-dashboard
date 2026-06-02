# Wger MCP через supergateway-bridge — implementation plan

**Task:** docs/ai/14-mcp-wger-supergateway/14-mcp-wger-supergateway-task.md
**Complexity:** simple
**Mode:** inline
**Parallel:** false

## Design decisions

### DD-1: Bridge-образ вместо native HTTP

**Decision:** Обернуть `@juxsta/wger-mcp` общим образом `services/_mcp/` (supergateway), а не запускать нативный HTTP-образ.
**Rationale:** Пакет stdio-only, официального HTTP-образа нет — это случай **Bridge** по таблице `docs/mcp/CONVENTIONS.md` §1. Образ `services/_mcp/Dockerfile` уже параметризован build-arg `MCP_PKG` и отдаёт streamable-HTTP на `8000` с health `/healthz`.
**Alternative:** Форк или собственный FastMCP — отклонено: спайк показал, что `WGER_API_URL` настраивается, обёртка не нужна.

### DD-2: Пакет `@juxsta/wger-mcp@1.1.1` (scoped, пин)

**Decision:** `build.args.MCP_PKG: "@juxsta/wger-mcp@1.1.1"`.
**Rationale:** Scoped-пакет от автора из тикета (12 tools, node≥18, npm latest 1.1.1). Bridge ставит его глобально на этапе сборки и резолвит через `npx -y`.
**Alternative:** Unscoped `wger-mcp` на npm — отклонено: другой проект; `:latest` — отклонено: конвенция требует пин.

### DD-3: Upstream `http://wger-nginx/api/v2`

**Decision:** `WGER_API_URL: http://wger-nginx/api/v2`, `depends_on: wger-nginx` (`condition: service_started`).
**Rationale:** Совпадает с таблицей внутренних хостов `docs/mcp/CONVENTIONS.md` §3 (Wger → `http://wger-nginx:80`); запросы идут по сети `internal`, не на публичный `wger.de`.
**Alternative:** `http://wger-web:8000/api/v2` напрямую — отклонено пользователем в пользу консистентности с конвенцией.

### DD-4: Секрет через неймспейс `.env`

**Decision:** `WGER_API_KEY: ${WGER_MCP_TOKEN:-}` в `environment:`.
**Rationale:** `docs/mcp/CONVENTIONS.md` §4 — токен живёт в корневом `.env` под `WGER_MCP_TOKEN` (плейсхолдер уже есть, строка 117) и мапится на имя, которое ждёт образ (`WGER_API_KEY`). Внутренний URL хардкодится, новой env-переменной не заводим.

## Tasks

### Task 1: Добавить сервис `mcp-wger` в docker-compose.yml

- **Files:** `docker-compose.yml` (edit — вставить блок после `wger-celery-beat`, заканчивается на строке ~413, до секции `volumes:` строка 527)
- **Depends on:** none
- **Scope:** S
- **What:** Добавить bridge-контейнер `mcp-wger`, оборачивающий `@juxsta/wger-mcp@1.1.1` и направленный на внутренний wger-инстанс.
- **How:** Скопировать структуру bridge-сниппета из `docs/mcp/CONVENTIONS.md` §6 / `services/_mcp/README.md`. Поля блока:
  - `build.context: ./services/_mcp`, `build.args.MCP_PKG: "@juxsta/wger-mcp@1.1.1"`
  - `restart: unless-stopped`
  - `depends_on.wger-nginx.condition: service_started`
  - `environment:` → `WGER_API_URL: http://wger-nginx/api/v2`, `WGER_API_KEY: ${WGER_MCP_TOKEN:-}`
  - `expose: ["8000"]`, `ports: - ${WGER_MCP_PORT:-}:8000`
  - `healthcheck.test: ["CMD","wget","-qO-","http://localhost:8000/healthz"]` (interval 30s, timeout 5s, retries 5, start_period 20s)
  - `deploy.resources.limits.memory: 128M`
  - `networks: [internal, dokploy-network]`
  - Traefik-labels НЕ добавлять.
- **Context:** `docs/mcp/CONVENTIONS.md` §3,§4,§6; `services/_mcp/README.md` (compose-сниппет); `services/_mcp/Dockerfile` (контракт `MCP_PKG`/health); `docker-compose.yml:205-413` (соседние wger-блоки, формат); `.env.example:117,125` (плейсхолдеры).
- **Verify:** `docker compose config -q` — без ошибок; в выводе `docker compose config` сервис `mcp-wger` присутствует с `MCP_PKG=@juxsta/wger-mcp@1.1.1`, `WGER_API_URL=http://wger-nginx/api/v2`.

### Task 2: Validation

- **Files:** —
- **Depends on:** Task 1
- **Scope:** S
- **What:** Проверить целостность compose и поднятие bridge-контейнера.
- **How:** Валидировать конфиг, собрать и поднять только `mcp-wger`, проверить health и MCP-эндпоинт.
- **Context:** —
- **Verify:**
  - `docker compose config -q` — зелёный
  - `WGER_MCP_PORT=8080 docker compose up -d --build mcp-wger` → контейнер `healthy`
  - `curl -fsS http://localhost:8080/healthz` → `ok`
  - `curl -fsS http://localhost:8080/mcp` → streamable-HTTP отвечает (не 404)
  - `docker compose logs mcp-wger` → supergateway обернул `@juxsta/wger-mcp`, обращений к `wger.de` нет

## Execution

- **Mode:** inline
- **Parallel:** false
- **Reasoning:** Одно изменение в одном файле плюс валидация — последовательно, без параллельных групп.
- **Order:**
  Task 1 → Task 2

## Verification

- `docker compose config -q` → без ошибок, сервис `mcp-wger` присутствует с `build.args.MCP_PKG=@juxsta/wger-mcp@1.1.1`.
- `WGER_MCP_PORT=8080 docker compose up -d --build mcp-wger` → контейнер `healthy`; `curl -fsS http://localhost:8080/healthz` → `ok` (health-эндпоинт supergateway).
- `curl -fsS http://localhost:8080/mcp` отвечает streamable-HTTP (MCP-инициализация, не 404).
- Логи `docker compose logs mcp-wger` → supergateway стартовал, обёрнут `@juxsta/wger-mcp`, обращений к публичному `wger.de` нет (запросы идут на `wger-nginx`).
- **Runbook (внешние UI):** в Dokploy UI создан домен `mcp-wger.dashboard.example.com` → порт `8000`; в Hermes зарегистрирован `https://mcp-wger.dashboard.example.com/mcp`.
- **Round-trip из Hermes:** прочитать список тренировок и создать тренировку через wger-MCP — данные появляются в UI self-hosted wger (не на `wger.de`). Подтверждает, что `WGER_API_URL` указывает на внутренний инстанс и `WGER_MCP_TOKEN` валиден (токен генерируется в UI wger).

## Materials

- [Issue #14 — [wger] MCP через supergateway](https://github.com/prineycom/svc-personal-dashboard/issues/14)
- [Epic #9](https://github.com/prineycom/svc-personal-dashboard/issues/9) · зависит от [#10](https://github.com/prineycom/svc-personal-dashboard/issues/10)
- [Juxsta/wger-mcp (GitHub)](https://github.com/Juxsta/wger-mcp) · [@juxsta/wger-mcp (npm, 1.1.1)](https://www.npmjs.com/package/@juxsta/wger-mcp) — 12 tools, env: `WGER_API_KEY` / `WGER_API_URL`
- [supergateway](https://github.com/supercorp-ai/supergateway)
- `docs/mcp/CONVENTIONS.md` · `docs/adr/0007-mcp-integration-topology.md` · `CONTEXT.md` (термины `MCP Endpoint`, `Bridge`)
- `services/_mcp/Dockerfile` · `services/_mcp/README.md` · `services/wger/nginx.conf`
