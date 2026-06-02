# Firefly III MCP — нативный HTTP-образ

**Slug:** 13-firefly-mcp-native
**Ticket:** https://github.com/prineycom/svc-personal-dashboard/issues/13
**Complexity:** simple
**Type:** general

## Task

Добавить контейнер `mcp-firefly` в корневой `docker-compose.yml` из нативного образа `ghcr.io/fabianonetto/mcp-server-firefly-iii`, подключённый к `firefly-app` по сети `internal`.

## Context

### Area architecture

Blueprint — плоский корневой `docker-compose.yml` (все контейнеры в одном файле, без `include`). MCP-слой описан в `docs/mcp/CONVENTIONS.md` и [ADR 0007](../../adr/0007-mcp-integration-topology.md): каждое направление — отдельный MCP-контейнер, отдаёт HTTP на порту `8000`, на сетях `internal` + `dokploy-network`, без `traefik`-labels (поддомен регистрируется в Dokploy UI). MCP ходит к своему сервису по внутреннему хосту, наружу через Tailscale выходит только Hermes → MCP.

Firefly III — native-кейс (официальный образ с HTTP при заданном `PORT`), мост `services/_mcp/` не нужен. Образ читает `FIREFLY_URL`, `FIREFLY_TOKEN`, `PORT`; при заданном `PORT` поднимает SSE-транспорт: `GET /sse` + `POST /messages`. Полный URL для Hermes — `https://mcp-firefly.dashboard.example.com/sse` (не `/mcp`). Дедицированного `/healthz` у образа нет; стабильный GET 200 отдаёт `GET /openapi.json`.

### Files to change

- `docker-compose.yml:201` — вставить блок `mcp-firefly:` после `firefly-cron` (заканчивается на строке 201, `networks: [internal]`), перед комментарием `# ── Wger`.
- `.env.example:116` — ключ `FIREFLY_MCP_TOKEN=` уже есть; добавить рядом escape-hatch `FIREFLY_MCP_PORT=` (по образцу `FIREFLY_PORT=8080` на `.env.example:52`) и пометить токен как Firefly Personal Access Token.
- `docs/mcp/CONVENTIONS.md` §6 Native (Firefly) — поправить сниппет: healthcheck на `/openapi.json`, путь Hermes `/sse`, пин по дайджесту.

### Patterns to reuse

- `docs/mcp/CONVENTIONS.md` §6 «Native (Firefly III)» — готовый compose-сниппет (env-маппинг `FIREFLY_TOKEN: ${FIREFLY_MCP_TOKEN:-}`, `expose: 8000`, `ports: ${FIREFLY_MCP_PORT:-}:8000`, `deploy.resources.limits.memory: 128M`, обе сети). Взять за основу, исправив healthcheck и пин.
- `docker-compose.yml:134` `firefly-app:` — `depends_on` целится сюда (`condition: service_started`); внутренний upstream `http://firefly-app:8080`.
- `docker-compose.yml:201` `firefly-cron` — образец `networks`, `deploy.resources.limits`, `restart: unless-stopped` для соседнего блока.
- `docker-compose.yml:535` `networks:` — `internal` (`internal: true`) + `dokploy-network` (`external: true`) уже определены, новые сети не нужны.

### Tests

Автоматических тестов в репозитории нет (infra/compose-репо). Покрытие — ручная проверка из секции Verification. Гэп тестов учтён в оценке сложности.

## Requirements

1. Добавить сервис `mcp-firefly` в `docker-compose.yml`: образ `ghcr.io/fabianonetto/mcp-server-firefly-iii@sha256:46dce54fdca3f0b919052bad9bf04a17fb0d4deed63ee5a871eca1d3bbbf516a` (= тег `sha-ac4303c`/`main` от 2026-05-05; перепроверить актуальный дайджест при имплементации).
2. Прокинуть `environment`: `FIREFLY_URL: http://firefly-app:8080`, `FIREFLY_TOKEN: ${FIREFLY_MCP_TOKEN:-}`, `PORT: "8000"`.
3. `depends_on: firefly-app` (`condition: service_started`), `restart: unless-stopped`, `deploy.resources.limits.memory: 128M`, сети `internal` + `dokploy-network`.
4. `expose: ["8000"]` и escape-hatch `ports: ["${FIREFLY_MCP_PORT:-}:8000"]`; без `traefik`-labels.
5. Healthcheck: `wget -qO- http://localhost:8000/openapi.json` (interval 30s, timeout 5s, retries 5, start_period 20s).
6. В `.env.example` добавить `FIREFLY_MCP_PORT=` рядом с `FIREFLY_MCP_TOKEN=` и комментарий, что токен — Firefly Personal Access Token (генерируется в UI Firefly: Options → Profile → OAuth → Personal Access Tokens).
7. Поправить `docs/mcp/CONVENTIONS.md` §6 Native (Firefly): healthcheck на `/openapi.json`, путь эндпоинта Hermes `/sse`, пин по дайджесту вместо `:<pin>`.

## Constraints

- Не добавлять `traefik`-labels в compose — роутинг и поддомен `mcp-firefly.dashboard.example.com` регистрируются в Dokploy UI.
- Не использовать мост `services/_mcp/` — Firefly это native-кейс, отдельной папки сервису не требуется.
- Не пиннить `:latest` — образ обновляется молча; пин строго по sha256-дайджесту.
- Не править `firefly-app`, `firefly-cron`, секцию `networks:` и существующие ключи `.env.example`.
- Не публиковать MCP-порт наружу постоянно — `ports:` только через пустой по умолчанию `${FIREFLY_MCP_PORT:-}`.
- Регистрацию в Hermes и Dokploy UI, деплой и Tailscale считать ручными ops-шагами вне изменений репозитория.

## Verification

- `docker compose config` → валидный конфиг, сервис `mcp-firefly` присутствует, образ с `@sha256:`.
- `FIREFLY_MCP_PORT=8765 docker compose up -d mcp-firefly firefly-app` → оба контейнера `running`, `mcp-firefly` health `healthy`.
- `curl -sf http://localhost:8765/openapi.json` → HTTP 200, JSON с OpenAPI-спецификацией.
- `curl -sN http://localhost:8765/sse` → открывается SSE-поток (заголовок `content-type: text/event-stream`).
- Edge: при пустом `FIREFLY_MCP_PORT` команда `docker compose config` не падает на маппинге `:8000`, наружу порт не публикуется.
- Edge: при недоступном `firefly-app` контейнер `mcp-firefly` поднимается, но MCP-вызовы к Firefly возвращают ошибку — это ожидаемо.

## Materials

- [Issue #13 — [firefly] MCP (нативный образ)](https://github.com/prineycom/svc-personal-dashboard/issues/13)
- [Epic #9](https://github.com/prineycom/svc-personal-dashboard/issues/9), зависит от [#10](https://github.com/prineycom/svc-personal-dashboard/issues/10)
- [fabianonetto/mcp-server-firefly-iii](https://github.com/fabianonetto/mcp-server-firefly-iii) — `FIREFLY_URL` / `FIREFLY_TOKEN` / `PORT`, эндпоинты `GET /sse`, `POST /messages`, `GET /openapi.json`
- Образ: `ghcr.io/fabianonetto/mcp-server-firefly-iii@sha256:46dce54fdca3f0b919052bad9bf04a17fb0d4deed63ee5a871eca1d3bbbf516a`
- `docs/mcp/CONVENTIONS.md` — конвенции MCP-слоя (§6 Native (Firefly III))
- `docs/adr/0007-mcp-integration-topology.md` — топология интеграции MCP
- `docker-compose.yml:134` — блок `firefly-app`; `docker-compose.yml:201` — `firefly-cron`
- `.env.example:116` — `FIREFLY_MCP_TOKEN=`
