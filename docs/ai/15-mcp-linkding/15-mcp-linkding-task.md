# Linkding MCP (нативный образ)

**Slug:** 15-mcp-linkding
**Ticket:** https://github.com/prineycom/svc-personal-dashboard/issues/15
**Complexity:** simple
**Type:** general

## Task

Добавить нативный контейнер `ghcr.io/chickenzord/linkding-mcp:v0.1.6` в корневой `docker-compose.yml` как MCP Endpoint для Linkding.

## Context

### Area architecture

Blueprint — плоский монорепо-`docker-compose.yml` (12 контейнеров, без `include`).
MCP-слой описан в [`docs/mcp/CONVENTIONS.md`](../../mcp/CONVENTIONS.md) и
[ADR 0007](../../adr/0007-mcp-integration-topology.md): каждое направление — отдельный
контейнер `mcp-<svc>`, отдаёт HTTP на внутреннем порту `8000`, на сетях `internal` +
`dokploy-network`, без `ports:` (кроме escape-hatch для локального теста), без
Traefik-labels (роутинг задаётся в Dokploy UI). Защита — Tailscale.

`mcp-linkding` ходит к сервису Linkding по `internal`: upstream `http://linkding:9090`
(см. таблицу в CONVENTIONS.md §3). Наружу через Tailscale выходит только Hermes → MCP.

Это **первый** MCP-контейнер в compose — других блоков `mcp-*` пока нет.

Образ `chickenzord/linkding-mcp` (Go, 3 инструмента: `search_bookmarks`,
`create_bookmark`, `get_tags`) — нативный HTTP, запускается субкомандой `http`.
Читает env: `LINKDING_URL` (required), `LINKDING_API_TOKEN` (required),
`BIND_ADDR` (default `:8080`). Эндпоинты: `POST /mcp/v1/initialize`,
`POST /mcp/v1/tools/list`, `POST /mcp/v1/tools/call` — кастомный REST-шейп,
не стандартный streamable-HTTP `/mcp`. Документированного health-эндпоинта нет.

### Files to change

- `docker-compose.yml:424-451` — блок сервиса `linkding`; новый сервис `mcp-linkding`
  добавить сразу после него (перед блоком `beaverhabits` на строке 453).
- `docker-compose.yml:535-540` — сети `internal` + `dokploy-network` уже определены,
  менять не требуется.
- `.env.example:118` (`LINKDING_MCP_TOKEN=`) и `.env.example:126` (`LINKDING_MCP_PORT=`)
  — плейсхолдеры уже есть. Уточнить комментарий: токен генерируется в UI Linkding
  (Settings → Integrations → REST API), мапится в `environment` на `LINKDING_API_TOKEN`.
- `services/linkding/.env.example` — при необходимости добавить ссылку на MCP-блок
  (опционально, документация сервиса).

### Patterns to reuse

- `docs/mcp/CONVENTIONS.md` §6 «Native (Firefly III)» — точный образец compose-блока:
  `restart`, `depends_on … condition: service_started`, `environment` с маппингом
  `<SVC>_MCP_TOKEN` → env образа, `expose: 8000`, `ports: ${LINKDING_MCP_PORT:-}:8000`,
  `deploy.resources.limits.memory: 128M`, сети.
- `docker-compose.yml:88-131` (`vikunja`) — образец `depends_on` и комментария о том,
  почему healthcheck пропущен у минимального образа без `wget`/`sh` (строки 115-118).
- `docker-compose.yml:425-451` (`linkding`) — образец стиля блока сервиса и memory-лимита.

### Tests

Автотестов в репозитории нет (инфраструктурный compose). Покрытие — статическая
валидация `docker compose config` и ручной verify через Hermes (см. Verification).

## Requirements

1. Добавить в `docker-compose.yml` сервис `mcp-linkding` с образом
   `ghcr.io/chickenzord/linkding-mcp:v0.1.6` и `command: ["http"]`.
2. Задать `BIND_ADDR: ":8000"`, `expose: ["8000"]`, `ports: - ${LINKDING_MCP_PORT:-}:8000`
   — порт `8000` по конвенции.
3. В `environment` задать `LINKDING_URL: http://linkding:9090` (internal upstream) и
   `LINKDING_API_TOKEN: ${LINKDING_MCP_TOKEN:-}` (маппинг неймспейса `.env` на env образа).
4. Добавить `depends_on: linkding: condition: service_started`, `restart: unless-stopped`,
   `deploy.resources.limits.memory: 128M`, сети `internal` + `dokploy-network`.
5. Healthcheck не задавать; добавить комментарий с причиной (минимальный Go-образ без
   shell/`wget` и без документированного health-эндпоинта — как у `vikunja`).
6. В `.env.example` уточнить комментарий к `LINKDING_MCP_TOKEN`: источник токена —
   UI Linkding, маппится на `LINKDING_API_TOKEN`.
7. Зафиксировать в `docs/mcp/CONVENTIONS.md` (таблица/раздел путей) полный URL для
   регистрации в Hermes: `https://mcp-linkding.dashboard.example.com/mcp/v1`
   (кастомный путь образа, не `/mcp`).

## Constraints

- Не добавлять Traefik-labels в compose — роутинг поддомена
  `mcp-linkding.dashboard.example.com` задаётся в Dokploy UI (CONVENTIONS.md §3).
- Не открывать порт наружу через `ports:` с фиксированным значением — только
  escape-hatch `${LINKDING_MCP_PORT:-}:8000` (на Dokploy пусто).
- Не менять блок сервиса `linkding` (`docker-compose.yml:425-451`) и определения сетей.
- Не хранить токен в `.env.example` или compose — только плейсхолдер `${LINKDING_MCP_TOKEN:-}`.
- Не использовать тег `:latest` — конвенция требует пиннинг (`:v0.1.6`).
- Фактическая регистрация в Hermes и AI-summary/теги — на стороне Hermes, вне этого
  репозитория; в задаче — только Blueprint (compose + `.env.example` + docs).

## Verification

- `docker compose config` → конфигурация валидна, сервис `mcp-linkding` присутствует,
  образ `ghcr.io/chickenzord/linkding-mcp:v0.1.6`, без Traefik-labels.
- `LINKDING_MCP_PORT=8100 docker compose up -d linkding mcp-linkding` →
  оба контейнера в статусе running.
- `curl -s -X POST http://localhost:8100/mcp/v1/tools/list` → ответ содержит инструменты
  `search_bookmarks`, `create_bookmark`, `get_tags`.
- `grep -c "linkding-mcp:v0.1.6" docker-compose.yml` → `1` (тег запиннен, не `latest`).
- Ops-шаг (вне репо): зарегистрировать `https://mcp-linkding.dashboard.example.com/mcp/v1`
  в Hermes; сохранить и найти закладку из Hermes → закладка появляется в UI Linkding.
- Edge case: при пустом `LINKDING_MCP_TOKEN` контейнер стартует, но вызовы к Linkding API
  возвращают ошибку авторизации — токен обязателен в проде.

## Materials

- [Issue #15](https://github.com/prineycom/svc-personal-dashboard/issues/15)
- [chickenzord/linkding-mcp](https://github.com/chickenzord/linkding-mcp) — образ `ghcr.io/chickenzord/linkding-mcp:v0.1.6`
- `docs/mcp/CONVENTIONS.md` — §6 Native (Firefly III), §3 сеть/роутинг/upstream
- `docs/adr/0007-mcp-integration-topology.md`
- `docker-compose.yml:424-451` — блок `linkding`
- `.env.example:108-128` — MCP-токены и порты
