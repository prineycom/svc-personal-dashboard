# Firefly III MCP — нативный HTTP-образ — implementation plan

**Task:** docs/ai/13-firefly-mcp-native/13-firefly-mcp-native-task.md
**Complexity:** simple
**Mode:** inline
**Parallel:** false

## Design decisions

### DD-1: Запуск нативного образа без моста

**Decision:** Запускать `ghcr.io/fabianonetto/mcp-server-firefly-iii` напрямую отдельным сервисом `mcp-firefly` в корневом `docker-compose.yml`, без `services/_mcp/`.
**Rationale:** Образ поднимает HTTP/SSE при заданном `PORT` (`docs/mcp/CONVENTIONS.md` §1, таблица транспортов). Native-кейсу своя папка не нужна (`docs/mcp/CONVENTIONS.md` §2).
**Alternative:** Обернуть через мост `services/_mcp/` — отклонено: у образа есть нативный HTTP, мост избыточен.

### DD-2: Пин по sha256-дайджесту

**Decision:** `image: ghcr.io/fabianonetto/mcp-server-firefly-iii@sha256:46dce54fdca3f0b919052bad9bf04a17fb0d4deed63ee5a871eca1d3bbbf516a`.
**Rationale:** Образ не публикует semver-теги (только `:latest`/`:main`/`:sha-<commit>`); дайджест иммутабелен и переживает перезапись тега. Конвенция требует пиннить (`docs/mcp/CONVENTIONS.md` §5).
**Alternative:** `:latest` — отклонено: молчаливые обновления; тег `sha-ac4303c` — перезаписываем.

### DD-3: Healthcheck на /openapi.json, эндпоинт Hermes — /sse

**Decision:** Healthcheck `wget -qO- http://localhost:8000/openapi.json`; URL для Hermes — `…/sse`.
**Rationale:** У образа нет `/healthz`; стабильный GET 200 даёт `GET /openapi.json`, а MCP-транспорт — SSE (`GET /sse` + `POST /messages`) по README образа.
**Alternative:** `/healthz` из обобщённого сниппета — отклонено: у образа такого пути нет; `GET /sse` — стрим, `wget` зависает до таймаута.

### DD-4: Гранулярность коммитов

**Decision:** Два логических изменения: (1) `feat` — сервис в compose + ключи `.env.example`; (2) `docs` — правка сниппета в `CONVENTIONS.md`.
**Rationale:** Функциональное изменение и правка документации — разные типы по `commit-convention.md`; `.env.example` идёт вместе с сервисом, который его потребляет.
**Alternative:** Один коммит на всё — отклонено: смешивает `feat` и `docs`.

## Tasks

### Task 1: Добавить сервис mcp-firefly

- **Files:** `docker-compose.yml:201` (edit, вставка после блока `firefly-cron`), `.env.example:116` (edit)
- **Depends on:** none
- **Scope:** S
- **What:** Добавить контейнер `mcp-firefly` из нативного образа, подключённый к `firefly-app`, и добавить escape-hatch `FIREFLY_MCP_PORT` в `.env.example`.
- **How:**
  - Вставить блок `mcp-firefly:` после `firefly-cron` (заканчивается на `docker-compose.yml:201`), перед комментарием `# ── Wger`:
    - `image: ghcr.io/fabianonetto/mcp-server-firefly-iii@sha256:46dce54fdca3f0b919052bad9bf04a17fb0d4deed63ee5a871eca1d3bbbf516a`
    - `restart: unless-stopped`
    - `depends_on: { firefly-app: { condition: service_started } }`
    - `environment: FIREFLY_URL: http://firefly-app:8080`, `FIREFLY_TOKEN: ${FIREFLY_MCP_TOKEN:-}`, `PORT: "8000"`
    - `expose: ["8000"]`, `ports: ["${FIREFLY_MCP_PORT:-}:8000"]`
    - `healthcheck: test: ["CMD", "wget", "-qO-", "http://localhost:8000/openapi.json"]`, `interval: 30s`, `timeout: 5s`, `retries: 5`, `start_period: 20s`
    - `deploy: resources: limits: memory: 128M`
    - `networks: [internal, dokploy-network]`
    - Перед актуализацией пина перепроверить текущий дайджест: `gh api /users/fabianonetto/packages/container/mcp-server-firefly-iii/versions --jq '.[] | select(.metadata.container.tags[]?=="main") | .name'`
  - В `.env.example` рядом с `FIREFLY_MCP_TOKEN=` (строка 116) добавить `FIREFLY_MCP_PORT=` и комментарий, что `FIREFLY_MCP_TOKEN` — Firefly Personal Access Token (UI Firefly: Options → Profile → OAuth → Personal Access Tokens).
- **Context:** `docs/mcp/CONVENTIONS.md` §6 «Native (Firefly III)» (готовый сниппет); `docker-compose.yml:134-201` (блоки `firefly-app`/`firefly-cron` — образец `networks`/`deploy`); `docker-compose.yml:535` (сети уже определены); `.env.example:52` (`FIREFLY_PORT=8080`), `.env.example:108-119` (MCP-секция)
- **Verify:** `docker compose config -q` — без ошибок; `docker compose config | grep -A2 'mcp-firefly'` показывает образ с `@sha256:`

### Task 2: Поправить сниппет Firefly в CONVENTIONS.md

- **Files:** `docs/mcp/CONVENTIONS.md` (edit, §6 «Native (Firefly III)»)
- **Depends on:** none
- **Scope:** S
- **What:** Привести сниппет Native (Firefly III) в соответствие реальному образу.
- **How:**
  - В блоке `mcp-firefly` §6: заменить `image: ghcr.io/...:<pin>` на пин по `@sha256:` (тот же дайджест, что в Task 1).
  - Healthcheck `test` — заменить `/healthz` на `http://localhost:8000/openapi.json`.
  - В §3 (или примечании к сниппету) указать, что URL для Hermes у Firefly — `https://mcp-firefly.dashboard.example.com/sse` (образ отдаёт SSE: `GET /sse` + `POST /messages`), а не `/mcp`.
- **Context:** `docs/mcp/CONVENTIONS.md` §3 (путь эндпоинта), §5 (healthcheck/пин), §6 (сниппет Native)
- **Verify:** `grep -n '/healthz' docs/mcp/CONVENTIONS.md` не находит вхождений в блоке Firefly; `grep -n 'sha256\|/sse' docs/mcp/CONVENTIONS.md` показывает обновления

### Task 3: Validation

- **Files:** —
- **Depends on:** Task 1, Task 2
- **Scope:** S
- **What:** Прогнать валидацию compose и ручную проверку эндпоинта.
- **Context:** —
- **Verify:**
  - `docker compose config -q` — без ошибок
  - `FIREFLY_MCP_PORT=8765 docker compose up -d mcp-firefly firefly-app` → оба `running`, `mcp-firefly` `healthy`
  - `curl -sf http://localhost:8765/openapi.json` → HTTP 200, JSON
  - `curl -sN --max-time 2 http://localhost:8765/sse` → заголовок `content-type: text/event-stream`

## Execution

- **Mode:** inline
- **Parallel:** false
- **Reasoning:** Три маленькие задачи в одном репозитории без общих файлов; объём не оправдывает суб-агентов.
- **Order:**
  Task 1 → Task 2 → Task 3
  (Task 1 и Task 2 независимы по файлам, но выполняются последовательно inline; Task 3 — после обеих.)

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
