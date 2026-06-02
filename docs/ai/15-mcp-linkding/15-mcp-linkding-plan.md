# Linkding MCP (нативный образ) — implementation plan

**Task:** docs/ai/15-mcp-linkding/15-mcp-linkding-task.md
**Complexity:** simple
**Mode:** inline
**Parallel:** false

## Design decisions

### DD-1: Порт MCP — `BIND_ADDR=":8000"`

**Decision:** Задать `BIND_ADDR: ":8000"`, `expose: ["8000"]`, `ports: ${LINKDING_MCP_PORT:-}:8000`.
**Rationale:** Конвенция (`docs/mcp/CONVENTIONS.md` §1, §6) фиксирует порт `8000` для всех MCP-контейнеров; образ принимает `BIND_ADDR`, поэтому дефолт `:8080` переопределяется.
**Alternative:** Оставить дефолт `:8080` — отвергнуто: расходится с единым неймспейсом портов остальных MCP.

### DD-2: Healthcheck — не задавать

**Decision:** Не описывать `healthcheck`; добавить комментарий с причиной. `depends_on: linkding: condition: service_started`.
**Rationale:** Образ — минимальный Go-бинарь без shell/`wget` и без документированного health-эндпоинта; та же ситуация, что у `vikunja` (`docker-compose.yml:115-118`).
**Alternative:** POST-проба `/mcp/v1/tools/list` — отвергнуто: требует `wget`/`curl` в образе, которого там нет.

### DD-3: Тег образа — пин `:v0.1.6`

**Decision:** `image: ghcr.io/chickenzord/linkding-mcp:v0.1.6`, `command: ["http"]`.
**Rationale:** Конвенция §5 требует пиннинг тега; `v0.1.6` — последний релиз. Образ стартует HTTP-режим субкомандой `http`.
**Alternative:** `:latest` — отвергнуто: нарушает пиннинг.

### DD-4: Путь эндпоинта для Hermes — `/mcp/v1`

**Decision:** Зафиксировать в `docs/mcp/CONVENTIONS.md` полный URL `https://mcp-linkding.dashboard.example.com/mcp/v1` и пометить, что образ использует кастомный путь, не `/mcp`.
**Rationale:** Образ отдаёт `POST /mcp/v1/initialize|tools/list|tools/call` вместо стандартного streamable-HTTP `/mcp`; §3 конвенции прямо допускает свой путь у native-образов «сверяйтесь с README». Фактическая совместимость с Hermes проверяется на verify (ops-шаг).
**Alternative:** Зафиксировать `/mcp` — отвергнуто: образ такого пути не отдаёт.

## Tasks

### Task 1: Добавить контейнер `mcp-linkding` в `docker-compose.yml`

- **Files:** `docker-compose.yml:451` (edit — вставить блок после сервиса `linkding`, перед `beaverhabits` на :453), `.env.example:118` (edit — уточнить комментарий к `LINKDING_MCP_TOKEN`)
- **Depends on:** none
- **Scope:** S
- **What:** Добавить сервис `mcp-linkding` нативным образом по образцу «Native (Firefly III)» из конвенции; уточнить комментарий к токену в `.env.example`.
- **How:**
  - Блок `mcp-linkding`: `image: ghcr.io/chickenzord/linkding-mcp:v0.1.6`, `command: ["http"]`, `restart: unless-stopped`.
  - `depends_on: linkding: condition: service_started`.
  - `environment:` `LINKDING_URL: http://linkding:9090`, `LINKDING_API_TOKEN: ${LINKDING_MCP_TOKEN:-}`, `BIND_ADDR: ":8000"`.
  - `expose: ["8000"]`, `ports: - ${LINKDING_MCP_PORT:-}:8000` (escape-hatch для локального теста).
  - `deploy.resources.limits.memory: 128M`, `networks: [internal, dokploy-network]`.
  - Комментарий над блоком: healthcheck опущен — минимальный Go-образ без shell/`wget`, без health-эндпоинта (по аналогии с `vikunja`).
  - Без Traefik-labels (роутинг в Dokploy UI).
  - В `.env.example` уточнить комментарий к `LINKDING_MCP_TOKEN`: токен генерируется в UI Linkding (Settings → Integrations → REST API), мапится на `LINKDING_API_TOKEN`.
- **Context:** `docs/mcp/CONVENTIONS.md` §6 (Native Firefly III) и §3 (upstream-таблица); `docker-compose.yml:88-131` (vikunja — depends_on, комментарий о пропуске healthcheck), `docker-compose.yml:424-451` (linkding), `.env.example:108-128`.
- **Verify:** `docker compose config -q` — без ошибок; `docker compose config | grep -A2 'mcp-linkding:'` показывает образ `:v0.1.6`.

### Task 2: Задокументировать Linkding-эндпоинт в `docs/mcp/CONVENTIONS.md`

- **Files:** `docs/mcp/CONVENTIONS.md` (edit — раздел §3 «Путь эндпоинта»)
- **Depends on:** none
- **Scope:** S
- **What:** Зафиксировать URL для регистрации в Hermes и кастомный путь образа Linkding.
- **How:** В §3 (после абзаца «Путь эндпоинта») добавить заметку: Linkding-образ отдаёт `POST /mcp/v1/initialize|tools/list|tools/call`; полный URL для Hermes — `https://mcp-linkding.dashboard.example.com/mcp/v1` (не `/mcp`). Сохранить стиль документа.
- **Context:** `docs/mcp/CONVENTIONS.md` §3 (текущий абзац про путь и таблицу upstream).
- **Verify:** `grep -q 'mcp-linkding.dashboard.example.com/mcp/v1' docs/mcp/CONVENTIONS.md` — найдено.

### Task 3: Validation

- **Files:** —
- **Depends on:** Task 1, Task 2
- **Scope:** S
- **What:** Прогнать статическую валидацию compose и проверить пиннинг тега.
- **Context:** —
- **Verify:** `docker compose config -q` — без ошибок; `grep -c 'linkding-mcp:v0.1.6' docker-compose.yml` → `1`; `grep -c ':latest' docker-compose.yml` для блока mcp-linkding — отсутствует.

## Execution

- **Mode:** inline
- **Parallel:** false
- **Reasoning:** Три атомарные задачи, разные файлы, нет общего состояния — простая последовательная правка в одной сессии.
- **Order:**
  Task 1 → Task 2 → Task 3

## Verification

- `docker compose config` → конфигурация валидна, сервис `mcp-linkding` присутствует, образ `ghcr.io/chickenzord/linkding-mcp:v0.1.6`, без Traefik-labels.
- `LINKDING_MCP_PORT=8100 docker compose up -d linkding mcp-linkding` → оба контейнера в статусе running.
- `curl -s -X POST http://localhost:8100/mcp/v1/tools/list` → ответ содержит инструменты `search_bookmarks`, `create_bookmark`, `get_tags`.
- `grep -c "linkding-mcp:v0.1.6" docker-compose.yml` → `1` (тег запиннен, не `latest`).
- Ops-шаг (вне репо): зарегистрировать `https://mcp-linkding.dashboard.example.com/mcp/v1` в Hermes; сохранить и найти закладку из Hermes → закладка появляется в UI Linkding.
- Edge case: при пустом `LINKDING_MCP_TOKEN` контейнер стартует, но вызовы к Linkding API возвращают ошибку авторизации — токен обязателен в проде.

## Materials

- [Issue #15](https://github.com/prineycom/svc-personal-dashboard/issues/15)
- [chickenzord/linkding-mcp](https://github.com/chickenzord/linkding-mcp) — образ `ghcr.io/chickenzord/linkding-mcp:v0.1.6`
- `docs/mcp/CONVENTIONS.md` — §6 Native (Firefly III), §3 сеть/роутинг/upstream
- `docs/adr/0007-mcp-integration-topology.md`
- `docker-compose.yml:424-451` — блок `linkding`
- `.env.example:108-128` — MCP-токены и порты
