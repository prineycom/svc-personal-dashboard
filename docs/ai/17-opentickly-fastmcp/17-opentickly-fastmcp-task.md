# OpenTickly MCP: свой FastMCP

**Slug:** 17-opentickly-fastmcp
**Ticket:** https://github.com/prineycom/svc-personal-dashboard/issues/17
**Complexity:** complex
**Type:** general

## Task

Подключить OpenTickly к Hermes через native streamable-HTTP MCP с тулами `start_timer`, `stop_timer`, `list_time_entries`, `get_report`: сначала спайк-гейт на форк готового Toggl-MCP, при провале — свой Python + FastMCP в `services/opentickly/mcp/`.

## Context

### Area architecture

Hermes — единая точка входа; каждое self-hosted направление — отдельный MCP-контейнер в корневом `docker-compose.yml`, отдаёт streamable-HTTP на порту `8000`, регистрируется поддоменом `mcp-<svc>.dashboard.example.com` в Dokploy UI (см. `docs/mcp/CONVENTIONS.md`, `docs/adr/0007-mcp-integration-topology.md`). OpenTickly — первый MCP-контейнер в этом репозитории: ни одного блока `mcp-*` в compose ещё нет.

Поток данных: Hermes → (Tailscale) → `mcp-opentickly:8000/mcp` → (сеть `internal`) → upstream `http://opentickly:8080` (Toggl Track API v9 + Reports API v3). MCP наружу авторизации не имеет, защита — Tailscale.

OpenTickly = `correctroad/opentoggl`, Toggl API-совместим. Реализован как FastMCP (свой), категория `native` в таблице конвенций.

### Files to change

- `docker-compose.yml:486` — upstream-сервис `opentickly` (image `correctroad/opentoggl:latest`, internal host `http://opentickly:8080`, health `/readyz`). Не менять, использовать как `depends_on` для нового MCP.
- `docker-compose.yml` (после блока `opentickly`, ~`:519`) — добавить блок сервиса `mcp-opentickly` (native FastMCP).
- `services/opentickly/mcp/` — **новая папка**: исходники Python + FastMCP-сервера и `Dockerfile` (конвенция §2: «Свой FastMCP — в `services/<svc>/mcp/`»).
- `services/opentickly/.env.example` — описать переменные MCP (токен/base URL) рядом с уже существующим `OPENTICKLY_PORT`.
- корневой `.env.example:120,128` — ключи `OPENTICKLY_MCP_TOKEN=` и `OPENTICKLY_MCP_PORT=` уже заведены; значения не коммитим.

### Patterns to reuse

- **Native compose-сниппет** — `docs/mcp/CONVENTIONS.md` §6 (пример Firefly): `expose: 8000`, escape-hatch `ports: ${OPENTICKLY_MCP_PORT:-}:8000`, healthcheck `wget` против health-пути, `restart: unless-stopped`, `memory: 128M`, сети `internal` + `dokploy-network`, `depends_on` с `condition`.
- **Маппинг секретов** — конвенция §4: `OPENTICKLY_MCP_TOKEN` в корневом `.env` → в `environment:` мапится на var, которую ждёт MCP (напр. `TOGGL_API_TOKEN`). Base URL Toggl API = внутренний `http://opentickly:8080`.
- **Структура Dockerfile** — `services/_mcp/Dockerfile` как образец дисциплины: пин версий (никогда `:latest`), `EXPOSE 8000`, exec-форма CMD, конфиг из env. (Сам bridge не используется — OpenTickly native.)
- **Спайк-кандидаты на форк**: `verygoodplugins/mcp-toggl` (Python, с отчётами), `KyteProject/togglgo-mcp` (Go) — проверить override base URL на OpenTickly.

### Tests

В репозитории тестов нет нигде. Для своего FastMCP добавить минимальный smoke-тест на `pytest`: маппинг тулов и парсинг ответа Toggl API на замоканных данных (без сети). Полный Verify — ручной через Hermes.

## Requirements

1. **Спайк-гейт первым шагом.** Проверить `verygoodplugins/mcp-toggl` (и при необходимости `KyteProject/togglgo-mcp`) на возможность переопределить base URL Toggl API на OpenTickly. Зафиксировать результат (форк возможен / нет) в отчёте задачи. Если override base URL работает — форкаем; если нет — пишем свой Python + FastMCP.
2. **MCP с 4 тулами:** `start_timer`, `stop_timer`, `list_time_entries`, `get_report`. `get_report` бьёт по Toggl Reports API v3; в спайке подтвердить, что OpenTickly отдаёт Reports v3, и реализовать тул в этой же итерации.
3. **Native streamable-HTTP на порту `8000`**, эндпоинт `/mcp`, health-путь для healthcheck. Сервер ходит в upstream по `http://opentickly:8080` (сеть `internal`), не через публичный URL.
4. **`Dockerfile`** (Python) для своего FastMCP в `services/opentickly/mcp/`, либо образ форка. Пин версий зависимостей и базового образа.
5. **Блок `mcp-opentickly` в корневом `docker-compose.yml`** по native-шаблону §6: `depends_on: opentickly (service_healthy)`, `expose: 8000`, `ports: ${OPENTICKLY_MCP_PORT:-}:8000`, healthcheck `wget`, `restart: unless-stopped`, `memory: 128M`, сети `internal` + `dokploy-network`. Без `ports`-маппинга кроме escape-hatch и без Traefik-labels.
6. **Секреты по конвенции §4:** использовать `OPENTICKLY_MCP_TOKEN` из корневого `.env`, в `environment:` смапить на var образа (напр. `TOGGL_API_TOKEN`); base URL передать как `http://opentickly:8080`. Описать переменные в `services/opentickly/.env.example`. Ключи `OPENTICKLY_MCP_TOKEN` / `OPENTICKLY_MCP_PORT` в корневом `.env.example` уже есть — не дублировать.
7. **Минимальный smoke-тест** (`pytest`) для своего FastMCP: маппинг тулов и парсинг ответа Toggl API на замоканных данных.
8. **Регистрация в Hermes:** поддомен `mcp-opentickly.dashboard.example.com` → порт `8000` (в Dokploy UI), URL `https://mcp-opentickly.dashboard.example.com/mcp`. Шаг ручной — описать в отчёте/README.

## Constraints

- Не менять upstream-сервис `opentickly` в `docker-compose.yml` — только добавить `mcp-opentickly` и сослаться через `depends_on`.
- Не добавлять Traefik-labels в compose и не открывать `ports:` сверх escape-hatch `${OPENTICKLY_MCP_PORT:-}:8000` — роутинг задаётся в Dokploy UI.
- Не вводить новые имена env (`OPENTICKLY_URL`, `TOGGL_API_TOKEN` как отдельные ключи в `.env`) — следовать неймспейсу `OPENTICKLY_MCP_*`, маппинг на var образа делать в compose.
- Не использовать `:latest` для образа MCP и зависимостей — пинить версии.
- Не вводить собственную авторизацию на MCP-эндпоинте — защита Tailscale.
- Не ломать существующие сервисы в compose: новый блок не трогает общие `postgres`/`redis`/тома.
- Не коммитить реальные токены — только `.env.example`.

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
- `services/_mcp/Dockerfile` — образец дисциплины Dockerfile (пины, exec-CMD)
- `docker-compose.yml:486` — upstream-сервис `opentickly`
- `services/opentickly/.env.example`, корневой `.env.example:120,128`
