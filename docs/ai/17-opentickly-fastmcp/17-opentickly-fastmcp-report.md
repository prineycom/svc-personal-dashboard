# Report: 17-opentickly-fastmcp

**Plan:** docs/ai/17-opentickly-fastmcp/17-opentickly-fastmcp-plan.md
**Mode:** inline (sub-agent dispatch unavailable for yoke agent types; orchestrator executed directly)
**Status:** ✅ complete

## Tasks

| #   | Task                                  | Status  | Commit    | Concerns |
| --- | ------------------------------------- | ------- | --------- | -------- |
| 1   | Спайк — форк vs свой (gate)           | ✅ DONE | `809893c` | —        |
| 2   | Каркас пакета + клиент + транспорт    | ✅ DONE | `4e693bd` | —        |
| 3   | 4 тула поверх клиента                 | ✅ DONE | `11bc2a2` | —        |
| 4   | Dockerfile                            | ✅ DONE | `6e848ba` | см. ниже |
| 5   | Smoke-тесты                           | ✅ DONE | `0a38be0` | —        |
| 6   | mcp-opentickly в compose + env        | ✅ DONE | `28c3901` | см. ниже |
| 7   | README / регистрация в Hermes         | ✅ DONE | `f76abed` | —        |
| 8   | Validation                            | ✅ DONE | —         | —        |

## Post-implementation

| Step          | Status     | Commit    |
| ------------- | ---------- | --------- |
| Validate      | ✅ pass    | —         |
| Documentation | ⏭️ skipped | —         |
| Format        | ✅ done    | `3d702a2` |

## Concerns (minor)

### Task 1: спайк

Статически подтвердить набор Reports v3-эндпоинтов OpenTickly по публичному
репозиторию не удалось (`correctroad/opentoggl` недоступен). `get_report`
реализован под канонический путь Reports v3
(`/reports/api/v3/workspace/{wid}/search/time_entries`); рантайм-подтверждение —
на ручном Verify из Hermes против живого контейнера.

### Task 4 + Task 6: healthcheck без wget

`python:3.12-slim` не содержит `wget`/`curl`, поэтому healthcheck в compose —
не `wget` из примеров конвенции, а bundled-интерпретатор:
`python -c "urllib.request.urlopen('http://localhost:8000/healthz')"`. Путь
здоровья `/healthz` отдаёт 200 (проверено на запущенном контейнере).

### Spike outcome

Решение: **свой Python + FastMCP**. Оба кандидата на форк не дают override base
URL (`verygoodplugins/mcp-toggl` хардкодит `https://api.track.toggl.com/api/v9`
в исходниках; `KyteProject/togglgo-mcp` — Go, без отчётов). Подробности —
`17-opentickly-fastmcp-spike.md`.

## Validation

- `docker compose config -q` ✅ (валиден; warnings — только незаданный `POSTGRES_PASSWORD`, pre-existing)
- `ruff check .` ✅ (All checks passed)
- `pytest` ✅ (7 passed, 0 failed)
- `docker build services/opentickly/mcp` ✅
- Контейнер стартует, `/healthz` → 200, `/mcp` слушает (проверено `docker run`)

## Changes summary

| File                                              | Action   | Description |
| ------------------------------------------------- | -------- | ----------- |
| docs/ai/17-opentickly-fastmcp/…-spike.md          | created  | Решение форк-vs-свой |
| services/opentickly/mcp/pyproject.toml            | created  | Пакет, deps (fastmcp, httpx), dev (ruff/pytest/respx), ruff/pytest config |
| services/opentickly/mcp/opentickly_mcp/config.py  | created  | Конфиг из env (base URL, token, workspace), без import-side-effects |
| services/opentickly/mcp/opentickly_mcp/client.py  | created  | Async httpx-клиент: Track v9 + Reports v3, Basic-auth |
| services/opentickly/mcp/opentickly_mcp/server.py  | created  | FastMCP app, /healthz, 4 тула, streamable-HTTP :8000 /mcp |
| services/opentickly/mcp/opentickly_mcp/__init__.py| created  | Версия пакета |
| services/opentickly/mcp/Dockerfile                | created  | python:3.12-slim, EXPOSE 8000, console-script CMD |
| services/opentickly/mcp/tests/test_tools.py       | created  | 7 smoke-тестов (respx, без сети) |
| services/opentickly/mcp/.gitignore                | created  | .venv/, кэши |
| docker-compose.yml                                | modified | Сервис `mcp-opentickly` (native §6) |
| services/opentickly/.env.example                  | modified | Описание MCP-переменных |
| services/opentickly/mcp/README.md                 | created  | Тулы, конфиг, регистрация в Dokploy/Hermes |

## Commits

- `809893c` #17 docs(17-opentickly-fastmcp): record fork-vs-own spike decision
- `4e693bd` #17 feat(17-opentickly-fastmcp): scaffold FastMCP package, config and Toggl client
- `11bc2a2` #17 feat(17-opentickly-fastmcp): add start/stop/list/report tools
- `6e848ba` #17 feat(17-opentickly-fastmcp): add Dockerfile for native FastMCP image
- `0a38be0` #17 test(17-opentickly-fastmcp): add smoke tests for tools and client
- `28c3901` #17 feat(17-opentickly-fastmcp): add mcp-opentickly compose service and env
- `f76abed` #17 docs(17-opentickly-fastmcp): add MCP README with Hermes registration
- `3d702a2` #17 chore(17-opentickly-fastmcp): apply ruff format

## Remaining manual step

Регистрация в Hermes — ручная: в Dokploy UI завести поддомен
`mcp-opentickly.dashboard.example.com` → порт `8000`, затем подключить Hermes к
`https://mcp-opentickly.dashboard.example.com/mcp`. См. README.
