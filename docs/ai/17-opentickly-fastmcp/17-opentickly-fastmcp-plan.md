# OpenTickly MCP: свой FastMCP — implementation plan

**Task:** docs/ai/17-opentickly-fastmcp/17-opentickly-fastmcp-task.md
**Complexity:** complex
**Mode:** sub-agents
**Parallel:** true

## Design decisions

### DD-1: Спайк-гейт, базовый путь — свой FastMCP

**Decision:** Первой задачей — спайк на форк `verygoodplugins/mcp-toggl` / `KyteProject/togglgo-mcp` с override base URL и проверкой Reports v3 в OpenTickly. Результат фиксируется в `…-spike.md`. Implementation-задачи плана написаны под **свой Python + FastMCP** как baseline (рекомендованный fallback из тикета).
**Rationale:** Тикет требует спайк первым шагом; пользователь выбрал «спайк-гейт, затем свой». Свой путь контролируем и не зависит от чужого релиз-цикла.
**Alternative:** Сразу форк — отвергнут: override base URL не подтверждён; если спайк покажет, что форк дешевле, Task 2–5 пересматриваются (re-plan), остальное (compose/env/docs) переиспользуется.

### DD-2: Стек — Python 3.12 + FastMCP + httpx

**Decision:** Пакет `services/opentickly/mcp/` на `fastmcp`, HTTP-клиент к Toggl API на `httpx`, конфиг и dev-тулинг (`ruff`, `pytest`) в `pyproject.toml`.
**Rationale:** Конвенция (`docs/mcp/CONVENTIONS.md` §1–2) предписывает «свой FastMCP — native, в `services/<svc>/mcp/`». В репозитории Python-кода и тулинга ещё нет — пакет приносит свой `pyproject.toml`.
**Alternative:** `mcp` SDK напрямую — отвергнут: FastMCP даёт streamable-HTTP и регистрацию тулов из коробки, меньше boilerplate.

### DD-3: Транспорт — native streamable-HTTP на :8000, путь `/mcp`, health `/healthz`

**Decision:** `FastMCP.run(transport="streamable-http", host="0.0.0.0", port=8000)` отдаёт `/mcp`; добавить кастомный route `/healthz` (200 OK) на нижележащем Starlette-app под healthcheck compose.
**Rationale:** Конвенция §3: контейнер слушает `8000`, эндпоинт `/mcp`, healthcheck `wget` против health-пути; native-образы могут иметь свой путь.
**Alternative:** Healthcheck против `/mcp` — отвергнут: `/mcp` ждёт MCP-handshake, а не GET; отдельный `/healthz` чище.

### DD-4: Секреты и upstream — конвенция §4

**Decision:** Конфиг из env: `OPENTICKLY_MCP_TOKEN` (корневой `.env`) → в compose мапится на `TOGGL_API_TOKEN`; base URL upstream — `http://opentickly:8080` (сеть `internal`). Toggl-аутентификация — Basic (`<token>:api_token`).
**Rationale:** Конвенция §4 и уже заведённые ключи `OPENTICKLY_MCP_TOKEN` / `OPENTICKLY_MCP_PORT` в `.env.example:120,128`.
**Alternative:** Отдельные `OPENTICKLY_URL` / `TOGGL_API_TOKEN` из тикета — отвергнут конвенцией (constraint задачи).

## Tasks

### Task 1: Спайк — форк vs свой (gate)

- **Files:** `docs/ai/17-opentickly-fastmcp/17-opentickly-fastmcp-spike.md` (create)
- **Depends on:** none
- **Scope:** S
- **What:** Проверить `verygoodplugins/mcp-toggl` (Python, с отчётами) и `KyteProject/togglgo-mcp` (Go) на возможность override base URL на OpenTickly; подтвердить, что OpenTickly отдаёт Toggl Reports API v3.
- **How:** Прочитать README/конфиг обоих репо (`gh`/WebFetch), найти настройку base URL. Сверить набор эндпоинтов Reports v3 с OpenTickly (`correctroad/opentoggl`). Записать явное решение «форк / свой» с обоснованием. При выводе «форк дешевле» — пометить, что Task 2–5 требуют re-plan.
- **Context:** task-файл §«Patterns to reuse» (спайк-кандидаты), `docs/adr/0007-mcp-integration-topology.md`.
- **Verify:** файл `…-spike.md` содержит явное решение и обоснование по override base URL и Reports v3.

### Task 2: Каркас FastMCP-пакета + Toggl-клиент + транспорт

- **Files:** `services/opentickly/mcp/pyproject.toml` (create), `services/opentickly/mcp/opentickly_mcp/__init__.py` (create), `services/opentickly/mcp/opentickly_mcp/config.py` (create), `services/opentickly/mcp/opentickly_mcp/client.py` (create), `services/opentickly/mcp/opentickly_mcp/server.py` (create)
- **Depends on:** Task 1
- **Scope:** M
- **What:** Поднять пакет `opentickly_mcp` с конфигом из env, httpx-клиентом к Toggl API и FastMCP-приложением на streamable-HTTP :8000 (`/mcp`) с health-роутом `/healthz`.
- **How:** `pyproject.toml` с зависимостями `fastmcp`, `httpx` и dev-группой `ruff`, `pytest`, `respx` (пины). `config.py` читает `OPENTICKLY_BASE_URL` (default `http://opentickly:8080`) и `TOGGL_API_TOKEN`. `client.py` — httpx-клиент с Basic-auth (`<token>:api_token`), методы-обёртки над Track v9 / Reports v3. `server.py` создаёт `FastMCP(...)`, регистрирует `/healthz` на Starlette-app, `if __name__ == "__main__": mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)`.
- **Context:** `docs/mcp/CONVENTIONS.md` §3 (транспорт/пути), `services/_mcp/Dockerfile` (дисциплина пинов), DD-2/DD-3/DD-4.
- **Verify:** `cd services/opentickly/mcp && python -c "import opentickly_mcp.server"` без ошибок; `ruff check .` — green.

### Task 3: 4 тула поверх клиента

- **Files:** `services/opentickly/mcp/opentickly_mcp/server.py` (edit), `services/opentickly/mcp/opentickly_mcp/client.py` (edit)
- **Depends on:** Task 2
- **Scope:** M
- **What:** Реализовать тулы `start_timer`, `stop_timer`, `list_time_entries`, `get_report`.
- **How:** `start_timer` → `POST /api/v9/workspaces/{wid}/time_entries` (duration -1, start now); `stop_timer` → `PATCH /api/v9/workspaces/{wid}/time_entries/{id}/stop`; `list_time_entries` → `GET /api/v9/me/time_entries` (фильтры start/end); `get_report` → `POST /reports/api/v3/workspace/{wid}/search/time_entries` (Reports v3). Каждый тул — `@mcp.tool` с типизированными аргументами и понятным docstring. Ошибки upstream и stop без активного таймера — возвращать осмысленный текст тула, не падать.
- **Context:** Toggl Track API v9 + Reports v3 (см. Materials), `client.py` из Task 2.
- **Verify:** `python -c "import opentickly_mcp.server"` импортирует; в коде зарегистрированы ровно 4 тула; `ruff check .` — green.

### Task 4: Dockerfile для своего FastMCP

- **Files:** `services/opentickly/mcp/Dockerfile` (create)
- **Depends on:** Task 3
- **Scope:** S
- **What:** Собрать native-образ FastMCP-сервера.
- **How:** База `python:3.12-slim` (пин digest/тега), копировать пакет, `pip install .` (без dev-группы), `EXPOSE 8000`, exec-форма `CMD` запускает `python -m opentickly_mcp.server`. Никаких `:latest`.
- **Context:** `services/_mcp/Dockerfile` как образец (пины, exec-CMD, EXPOSE 8000), DD-3.
- **Verify:** `docker build -t mcp-opentickly-test services/opentickly/mcp` завершается успешно.

### Task 5: Smoke-тесты

- **Files:** `services/opentickly/mcp/tests/__init__.py` (create), `services/opentickly/mcp/tests/test_tools.py` (create)
- **Depends on:** Task 3
- **Scope:** S
- **What:** Минимальный pytest на маппинг тулов и парсинг ответа Toggl API на замоканных данных (без сети).
- **How:** Мокать httpx через `respx`; проверить, что `start_timer`/`stop_timer`/`list_time_entries`/`get_report` строят правильные запросы и парсят ответ; проверить ветку «stop без активного таймера» и пустой `get_report`.
- **Context:** `client.py`, `server.py` из Task 2–3.
- **Verify:** `cd services/opentickly/mcp && pytest` — green.

### Task 6: Блок mcp-opentickly в compose + env

- **Files:** `docker-compose.yml` (edit, после блока `opentickly` ~`:519`), `services/opentickly/.env.example` (edit)
- **Depends on:** Task 4
- **Scope:** M
- **What:** Добавить native-сервис `mcp-opentickly` по шаблону §6 и описать переменные MCP в service-`.env.example`.
- **How:** Блок: `build: context ./services/opentickly/mcp`, `depends_on: opentickly (condition: service_healthy)`, `environment:` `TOGGL_API_TOKEN: ${OPENTICKLY_MCP_TOKEN:-}` + `OPENTICKLY_BASE_URL: http://opentickly:8080`, `expose: ["8000"]`, `ports: ["${OPENTICKLY_MCP_PORT:-}:8000"]`, healthcheck `wget -qO- http://localhost:8000/healthz`, `restart: unless-stopped`, `memory: 128M`, сети `internal` + `dokploy-network`. Без Traefik-labels. В `services/opentickly/.env.example` описать `OPENTICKLY_MCP_TOKEN` и `OPENTICKLY_MCP_PORT` (ключи в корневом `.env.example` уже есть — не дублировать).
- **Context:** `docs/mcp/CONVENTIONS.md` §6 (native Firefly snippet), `docker-compose.yml:486` (upstream `opentickly`), DD-4.
- **Verify:** `docker compose config -q` — без ошибок; блок `mcp-opentickly` присутствует, Traefik-labels отсутствуют, `ports` только escape-hatch.

### Task 7: Документация регистрации в Hermes

- **Files:** `services/opentickly/mcp/README.md` (create)
- **Depends on:** Task 6
- **Scope:** S
- **What:** Описать ручной шаг регистрации в Dokploy UI и подключение Hermes.
- **How:** README: назначение сервиса, тулы, поддомен `mcp-opentickly.dashboard.example.com` → порт `8000` (в Dokploy UI, без Traefik-labels), URL `https://mcp-opentickly.dashboard.example.com/mcp`, health `/healthz`, ссылки на `CONVENTIONS.md` и ADR 0007.
- **Context:** `docs/mcp/CONVENTIONS.md` §3, `services/_mcp/README.md` как образец стиля.
- **Verify:** README документирует поддомен, путь `/mcp`, health `/healthz` и шаг Dokploy UI.

### Task 8: Validation

- **Files:** —
- **Depends on:** all
- **Scope:** S
- **What:** Прогнать полную проверку: compose-валидность, сборка образа, линт, тесты.
- **Context:** —
- **Verify:** `docker compose config -q && docker build -t mcp-opentickly-test services/opentickly/mcp && (cd services/opentickly/mcp && ruff check . && pytest)` — всё green.

## Execution

- **Mode:** sub-agents
- **Parallel:** true
- **Reasoning:** Complex, 8 задач в одном кодовом пакете с сильной последовательной связностью; распараллеливается только пара Dockerfile ∥ тесты после реализации тулов.
- **Order:**
  Task 1 (спайк-гейт)
  ─── barrier ───
  Task 2 → Task 3
  ─── barrier ───
  Group (parallel): Task 4, Task 5
  ─── barrier ───
  Task 6 → Task 7
  ─── barrier ───
  Task 8 (Validation)

## Verification

- `docker compose config -q` → без ошибок (compose валиден после добавления `mcp-opentickly`).
- `docker compose up -d opentickly mcp-opentickly` → оба контейнера `healthy`; `docker compose ps` показывает `mcp-opentickly` в статусе healthy.
- `wget -qO- http://localhost:${OPENTICKLY_MCP_PORT}/healthz` (или health-путь образа) → ответ 200.
- `pytest` в `services/opentickly/mcp/` → smoke-тесты зелёные.
- Из Hermes: `start_timer` создаёт запись времени в OpenTickly; `stop_timer` её останавливает; `list_time_entries` возвращает запись; `get_report` отдаёт отчёт (Reports v3).
- Спайк задокументирован: явное решение «форк / свой» с обоснованием по override base URL.
- Edge cases: `get_report` при отсутствии данных за период → пустой отчёт без ошибки; `stop_timer` без активного таймера → понятная ошибка тула; недоступный upstream `opentickly` → MCP стартует, тул возвращает ошибку соединения, не падает.

## Materials

- [Issue #17 — [opentickly] Свой FastMCP](https://github.com/prineycom/svc-personal-dashboard/issues/17)
- [Epic #9](https://github.com/prineycom/svc-personal-dashboard/issues/9) · зависит от [#10](https://github.com/prineycom/svc-personal-dashboard/issues/10)
- [verygoodplugins/mcp-toggl](https://github.com/verygoodplugins/mcp-toggl) — кандидат на форк (Python, с отчётами)
- [KyteProject/togglgo-mcp](https://github.com/KyteProject/togglgo-mcp) — кандидат на форк (Go)
- Toggl Track API v9 + Reports API v3 (совместимость OpenTickly)
- `docs/mcp/CONVENTIONS.md` — конвенции MCP-слоя (транспорт, размещение, секреты, сниппеты)
- `docs/adr/0007-mcp-integration-topology.md` — топология интеграции
- `services/_mcp/Dockerfile`, `services/_mcp/README.md` — образцы дисциплины
- `docker-compose.yml:486` — upstream-сервис `opentickly`
- `services/opentickly/.env.example`, корневой `.env.example:120,128`
