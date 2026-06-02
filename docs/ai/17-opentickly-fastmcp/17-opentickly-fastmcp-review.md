# Code Review: 17-opentickly-fastmcp

## Summary

### Context and goal

Подключение OpenTickly (Toggl-совместимый тайм-трекер) к Hermes через
собственный Python + FastMCP native MCP-контейнер с тулами `start_timer`,
`stop_timer`, `list_time_entries`, `get_report`. Спайк подтвердил выбор «свой»
поверх форка.

### Key code areas for review

1. **`opentickly_mcp/client.py:TogglClient`** — обёртка httpx над Track v9 /
   Reports v3, Toggl Basic-auth (`token:api_token`), обработка ошибок и кэш
   `workspace_id`.
2. **`opentickly_mcp/server.py`** — FastMCP app, lazy race-safe `get_client`,
   lifespan-закрытие клиента, `/healthz`, 4 тула, streamable-HTTP :8000 `/mcp`.
3. **`docker-compose.yml` (`mcp-opentickly`)** — native §6: depends_on healthy,
   expose 8000, escape-hatch port, python-healthcheck, 128M, без Traefik-labels.

### Complex decisions

1. **Healthcheck без wget** (`docker-compose.yml`) — `python:3.12-slim` не имеет
   `wget`/`curl`, поэтому проверка идёт через `python -c urllib.request`.
2. **Lazy config** (`server.py:get_client`) — `Config.from_env()` вызывается на
   первом тул-колле, чтобы импорт модуля не требовал токена (нужно для CI/тестов).

### Questions for the reviewer

1. Подтверждён ли набор Reports v3-эндпоинтов в текущей сборке OpenTickly
   (`correctroad/opentoggl`)? `get_report` бьёт по
   `/reports/api/v3/workspace/{wid}/search/time_entries`.

### Risks and impact

- **Reports v3 совместимость** OpenTickly не подтверждена статически — проверить
  на живом контейнере при ручном Verify.
- **Регистрация в Dokploy/Hermes** — ручной шаг вне кода (см. README).

### Tests and manual checks

**Auto-tests:** 7 smoke-тестов (respx, без сети) — построение запросов, парсинг,
пустой отчёт, «нет активного таймера», обёртка ошибки upstream.

**Manual scenarios:**

1. `docker compose up -d opentickly mcp-opentickly` → оба `healthy`.
2. Из Hermes `start_timer` → запись создана; `stop_timer` → остановлена;
   `list_time_entries` → запись видна; `get_report` → отчёт за период.

### Out of scope

- Регистрация поддомена в Dokploy UI (ручной шаг).
- Дополнительные тулы (projects, tags, current) — только 4 из тикета.

## Commits

| Hash    | Description |
| ------- | ----------- |
| 809893c | docs: record fork-vs-own spike decision |
| 4e693bd | feat: scaffold FastMCP package, config and Toggl client |
| 11bc2a2 | feat: add start/stop/list/report tools |
| 6e848ba | feat: add Dockerfile for native FastMCP image |
| 0a38be0 | test: add smoke tests for tools and client |
| 28c3901 | feat: add mcp-opentickly compose service and env |
| f76abed | docs: add MCP README with Hermes registration |
| 3d702a2 | chore: apply ruff format |
| 7a203e4 | docs: add execution report |
| 505cc84 | fix: fix 3 review issues |

## Changed Files

| File                                             | +/-   | Description |
| ------------------------------------------------ | ----- | ----------- |
| services/opentickly/mcp/opentickly_mcp/server.py | +135  | FastMCP app, lifespan, 4 тула |
| services/opentickly/mcp/opentickly_mcp/client.py | +115  | httpx-клиент Track v9 + Reports v3 |
| services/opentickly/mcp/tests/test_tools.py      | +117  | 7 smoke-тестов |
| services/opentickly/mcp/README.md                | +61   | Документация + регистрация |
| docker-compose.yml                               | +46   | Сервис mcp-opentickly |
| services/opentickly/mcp/pyproject.toml           | +37   | Пакет + конфиг тулинга |
| services/opentickly/mcp/opentickly_mcp/config.py | +31   | Конфиг из env |
| services/opentickly/mcp/Dockerfile               | +20   | Native образ, пин по digest |
| services/opentickly/.env.example                 | +11   | Описание MCP-переменных |

## Issues Found

| Severity | Score | Category        | File:line                          | Description |
| -------- | ----- | --------------- | ---------------------------------- | ----------- |
| Minor    | 35    | reproducibility | services/opentickly/mcp/Dockerfile:3 | База `python:3.12-slim` плавала по патчу |
| Minor    | 30    | performance     | opentickly_mcp/client.py:resolve_workspace_id | Лишний `GET /api/v9/me` на каждый вызов |
| Minor    | 25    | resource        | opentickly_mcp/server.py:get_client | Клиент не закрывался; гонка на первом вызове |

## Fixed Issues

| Issue                                   | Commit    | Description |
| --------------------------------------- | --------- | ----------- |
| База образа плавала по патчу            | `505cc84` | Пин по digest `sha256:090ba77…` |
| Лишний `/me` на каждый тул-колл         | `505cc84` | Кэш `_resolved_workspace_id` в клиенте |
| Клиент не закрывался / гонка get_client | `505cc84` | `asyncio.Lock` + lifespan-`aclose` |

## Skipped Issues

**All found issues were fixed.**

## Recommendations

- На ручном Verify подтвердить Reports v3 в OpenTickly (вопрос ревьюеру выше).
- Зарегистрировать поддомен `mcp-opentickly.dashboard.example.com` → `8000` в
  Dokploy UI и подключить Hermes к `/mcp`.
