# Wger MCP через supergateway-bridge

**Slug:** 14-mcp-wger-supergateway
**Ticket:** https://github.com/prineycom/svc-personal-dashboard/issues/14
**Complexity:** simple
**Type:** general

## Task

Добавить контейнер `mcp-wger` в корневой `docker-compose.yml`, обернув stdio-only пакет `@juxsta/wger-mcp` общим bridge-образом `services/_mcp/` и направив его на внутренний wger-инстанс.

## Context

### Area architecture

MCP-слой Blueprint: каждое self-hosted направление отдаёт streamable-HTTP на порту `8000` отдельным контейнером, Hermes ходит к нему через Traefik-поддомен `mcp-<svc>.dashboard.example.com` (защита — Tailscale). Wger-MCP — случай **Bridge**: у `@juxsta/wger-mcp` нет официального HTTP-образа, только stdio, поэтому его оборачивает общий supergateway-образ `services/_mcp/`. MCP ходит к wger по сети `internal` на внутренний хост, наружу через Tailscale выходит только Hermes → MCP. Архитектура — [ADR 0007](../../adr/0007-mcp-integration-topology.md), конвенции — [docs/mcp/CONVENTIONS.md](../../mcp/CONVENTIONS.md).

**Спайк закрыт (выполнен при подготовке задачи):** URL self-hosted инстанса у `@juxsta/wger-mcp` настраивается через `WGER_API_URL` (дефолт `https://wger.de/api/v2`). Форк или собственный FastMCP **не нужны** — bridge применяется напрямую.

### Files to change

- `docker-compose.yml` — добавить блок `mcp-wger` после блока `wger-celery-beat` (заканчивается на строке ~413, до секции `volumes:` на строке 527). Соседние bridge/MCP-блоки в этом файле пока отсутствуют — `mcp-wger` первый.
- `.env.example` — плейсхолдеры уже есть: `WGER_MCP_TOKEN=` (строка 117) и `WGER_MCP_PORT=` (строка 125). Менять не требуется; добавлять `WGER_API_URL` в `.env` не нужно (внутренний хост хардкодится в `environment:` compose).

### Patterns to reuse

- `docs/mcp/CONVENTIONS.md` §6 «Bridge (Vikunja)» и `services/_mcp/README.md` — готовый compose-сниппет bridge-сервиса: скопировать структуру, заменить имя, `MCP_PKG`, `environment:` и `depends_on`.
- `services/_mcp/Dockerfile` — общий образ, параметризуется build-arg `MCP_PKG` (формат `<pkg>@<version>`); supergateway отдаёт `/mcp` и health `/healthz` на порту `8000`. Менять Dockerfile не нужно.
- Внутренний upstream wger — таблица в `docs/mcp/CONVENTIONS.md` §3: `http://wger-nginx:80`. nginx-конфиг проксирует на `wger-web:8000` (`services/wger/nginx.conf`).
- Маппинг секрета — `docs/mcp/CONVENTIONS.md` §4: токен лежит в `.env` под неймспейсом `WGER_MCP_TOKEN`, в `environment:` мапится на имя, которое ждёт образ.

### Tests

Автотестов в репозитории нет (инфраструктурный монорепо, без тест-сьюта). Проверка — операционная: `docker compose config`, поднятие контейнера, health-эндпоинт, round-trip из Hermes (см. Verification).

## Requirements

1. Добавить сервис `mcp-wger` в `docker-compose.yml`, собираемый из общего bridge-образа: `build.context: ./services/_mcp`, `build.args.MCP_PKG: "@juxsta/wger-mcp@1.1.1"` (scoped-пакет; unscoped `wger-mcp` на npm — другой проект, не использовать).
2. В `environment:` задать `WGER_API_URL: http://wger-nginx/api/v2` (внутренний хост по сети `internal`) и `WGER_API_KEY: ${WGER_MCP_TOKEN:-}` (маппинг неймспейса `.env` на имя переменной образа).
3. `depends_on: wger-nginx` с `condition: service_started`.
4. Сеть `internal` + `dokploy-network`; `expose: ["8000"]`; escape-hatch `ports: - ${WGER_MCP_PORT:-}:8000` для локального теста.
5. `restart: unless-stopped`, лимит `memory: 128M`, healthcheck `wget -qO- http://localhost:8000/healthz` (interval 30s, timeout 5s, retries 5, start_period 20s) — как в bridge-сниппете конвенций.
6. Зарегистрировать поддомен `mcp-wger.dashboard.example.com` → порт `8000` **в Dokploy UI** (Traefik-labels в compose не добавлять) и зарегистрировать эндпоинт `https://mcp-wger.dashboard.example.com/mcp` в Hermes — оформить как операционный runbook в разделе Verification (внешние UI, репозиторием не автоматизируются).

## Constraints

- Не редактировать `services/_mcp/Dockerfile` и `services/_mcp/README.md` — образ общий и уже параметризован `MCP_PKG`.
- Не добавлять Traefik-labels в `docker-compose.yml` — источник роутинга Dokploy UI (как у всех сервисов).
- Не плодить новую env-переменную под URL: внутренний хост `http://wger-nginx/api/v2` хардкодится в `environment:`, как `VIKUNJA_URL` в примере конвенций.
- Не использовать unscoped пакет `wger-mcp` (другой автор) и не оставлять `:latest` — пин обязателен.
- Не трогать существующие блоки `wger-web`, `wger-nginx`, `wger-celery-worker`, `wger-celery-beat` и общий `.env.example`-неймспейс.

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
- [Juxsta/wger-mcp (GitHub)](https://github.com/Juxsta/wger-mcp) · [@juxsta/wger-mcp (npm, 1.1.1)](https://www.npmjs.com/package/@juxsta/wger-mcp) — 9 tools (проверено вживую; README заявляет 12), env: `WGER_API_KEY` / `WGER_API_URL`
- [supergateway](https://github.com/supercorp-ai/supergateway)
- `docs/mcp/CONVENTIONS.md` · `docs/adr/0007-mcp-integration-topology.md` · `CONTEXT.md` (термины `MCP Endpoint`, `Bridge`)
- `services/_mcp/Dockerfile` · `services/_mcp/README.md` · `services/wger/nginx.conf`
