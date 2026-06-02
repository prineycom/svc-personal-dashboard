# Соглашения MCP-контейнеров в Blueprint — implementation plan

**Task:** GitHub issue #10 — https://github.com/prineycom/svc-personal-dashboard/issues/10
**Complexity:** simple
**Mode:** inline
**Parallel:** false

> Источник — GitHub issue (не файл `docs/ai/*-task.md`). Поля Slug/Complexity/Context выведены из тела issue, [ADR 0007](../../adr/0007-mcp-integration-topology.md) и текущего `docker-compose.yml`.
> **Slug:** `10-mcp-conventions` · **Ticket:** #10 · **Type:** general (infra/docs)

## Design decisions

### DD-1: Размещение MCP-артефактов

**Decision:** Переиспользуемый bridge-образ — в `services/_mcp/` (Dockerfile + README). Конвенции — в `docs/mcp/CONVENTIONS.md`. Собственные FastMCP (позже) лягут в `services/<svc>/mcp/`.
**Rationale:** Префикс `_` отделяет шаблон от запускаемых сервисов (`services/vikunja/`, `services/wger/` — реальные); один общий bridge-Dockerfile не дублируется между Vikunja и Wger. Соответствует изоляции «Service Directory» из `CONTEXT.md`.
**Alternative:** Класть Dockerfile в `services/vikunja/mcp/` — отвергнуто: привязывает общий шаблон к одному сервису, второй (Wger) копировал бы его.

### DD-2: Транспорт-мост для stdio-MCP

**Decision:** Один параметризованный образ на `node:22-alpine` с `supergateway`, оборачивающий stdio-MCP в streamable-HTTP на порту 8000. Пакет MCP передаётся через build-arg `MCP_PKG` (с пином версии). Применяется только к MCP без нативного HTTP/образа (Vikunja, Wger).
**Rationale:** supergateway — де-факто stdio↔HTTP мост; один образ + build-arg покрывает оба bridge-сервиса. Firefly III (`PORT`) и Linkding (`BIND_ADDR`) имеют нативный HTTP и официальный образ — мост им не нужен (ADR 0007).
**Alternative:** `mcpo` или свой Node-враппер — отвергнуто: больше кода ради того же результата.

### DD-3: Роутинг и сеть

**Decision:** MCP-контейнеры — на сетях `internal` + `dokploy-network`, **без `ports:`** (кроме escape-hatch `${<SVC>_MCP_PORT:-}:8000` для локалки), слушают порт 8000. Поддомен `mcp-<svc>.dashboard.example.com` регистрируется **в Dokploy UI**, Traefik-labels в compose **не добавляются**. MCP ходит к своему сервису по `internal` (например `http://vikunja:3456`), наружу через Tailscale выходит только Hermes→MCP.
**Rationale:** Повторяет существующее решение «routing source = Dokploy UI» (revert-коммит `00f26e5`, в compose labels нет). Трафик MCP→сервис остаётся внутри `internal` — не нужно гонять через Traefik/Tailscale.
**Alternative:** Traefik-labels в compose — отвергнуто: противоречит текущей конвенции проекта.

### DD-4: Именование секретов

**Decision:** Токены MCP в корневом `.env` с префиксом `<SVC>_MCP_TOKEN`; в `environment:`-блоке compose они мапятся на ту переменную, которую ждёт конкретный образ (например `FIREFLY_TOKEN: ${FIREFLY_MCP_TOKEN:-}`). URL сервиса задаётся внутренним именем хоста, не публичным.
**Rationale:** Сохраняет единый неймспейс в `.env` (как `VIKUNJA_*`, `WGER_*` сейчас), не требуя переименования env сторонних образов.
**Alternative:** Использовать имена переменных образов напрямую — отвергнуто: разнобой в `.env`, неочевидно что относится к MCP.

### DD-5: Healthcheck

**Decision:** Шаблон — `wget -qO- http://localhost:8000/<health>` (supergateway: `--healthEndpoint /healthz`; нативные образы — свой health/SSE-путь). `memory: 128M`, `restart: unless-stopped`, пин тега — как у остальных сервисов.
**Rationale:** Повторяет паттерн healthcheck/limits из текущего compose (opentickly `/readyz`, wger spider-check).
**Alternative:** Без healthcheck — отвергнуто: нарушает конвенцию «memory-лимит + healthcheck на каждом».

## Tasks

### Task 1: Bridge-образ и документ конвенций

- **Files:** `services/_mcp/Dockerfile` (create), `services/_mcp/README.md` (create), `docs/mcp/CONVENTIONS.md` (create)
- **Depends on:** none
- **Scope:** M
- **What:** Создать переиспользуемый supergateway-Dockerfile (DD-2) и центральный документ конвенций MCP-слоя (DD-1…DD-5) с copy-ready compose-блоками для двух случаев: «нативный образ» и «bridge».
- **How:**
  - `services/_mcp/Dockerfile`: `FROM node:22-alpine`; `ARG SUPERGATEWAY_VERSION=3.4.0`; `ARG MCP_PKG`; `ENV MCP_PKG=${MCP_PKG} MCP_PORT=8000`; `RUN npm install -g supergateway@${SUPERGATEWAY_VERSION} ${MCP_PKG}`; `EXPOSE 8000`; `CMD supergateway --stdio "npx -y ${MCP_PKG}" --outputTransport streamableHttp --port ${MCP_PORT} --healthEndpoint /healthz`. Комментарий: пинить и supergateway, и MCP_PKG, никогда `:latest`.
  - `services/_mcp/README.md`: как собирать per-service (`build.args.MCP_PKG`), ссылка на #12 (Vikunja) и #14 (Wger).
  - `docs/mcp/CONVENTIONS.md`: разделы — Размещение (DD-1), Транспорт native-vs-bridge (DD-2), Сеть и роутинг через Dokploy UI без labels (DD-3), Секреты `<SVC>_MCP_TOKEN` + маппинг (DD-4), Healthcheck/limits (DD-5). Два compose-сниппета: `mcp-firefly` (native image, `PORT`, env `FIREFLY_URL: http://firefly-app:8080`, `FIREFLY_TOKEN: ${FIREFLY_MCP_TOKEN:-}`) и `mcp-vikunja` (`build: ./services/_mcp` с `MCP_PKG`, env `VIKUNJA_URL: http://vikunja:3456`). Таблица внутренних upstream-хостов: vikunja:3456, firefly-app:8080, wger-nginx:80, linkding:9090, beaverhabits:8080, opentickly:8080. Ссылка на ADR 0007.
- **Context:** `docker-compose.yml:88-131` (Vikunja: networks/healthcheck/limits паттерн), `docker-compose.yml:485-520` (opentickly: healthcheck `/readyz`, env, networks), `docs/adr/0007-mcp-integration-topology.md` (per-service маппинг), `CONTEXT.md` (термины MCP Endpoint, Bridge).
- **Verify:** `docker build --build-arg MCP_PKG=@democratize-technology/vikunja-mcp@0.2.0 -t mcp-bridge-test services/_mcp` — образ собирается (нужна сеть/npm).

### Task 2: Вынести конвенции в точки входа

- **Files:** `.env.example` (edit), `README.md` (edit)
- **Depends on:** Task 1
- **Scope:** S
- **What:** Добавить в `.env.example` секцию MCP-токенов, в `README.md` — раздел про MCP-слой со ссылкой на `docs/mcp/CONVENTIONS.md` и ADR 0007.
- **How:**
  - `.env.example`: блок-комментарий `# ── MCP layer (stage 2) ──` + закомментированные `VIKUNJA_MCP_TOKEN=`, `FIREFLY_MCP_TOKEN=`, `WGER_MCP_TOKEN=`, `LINKDING_MCP_TOKEN=`, `BEAVERHABITS_MCP_TOKEN=`, `OPENTICKLY_MCP_TOKEN=` и опциональные `*_MCP_PORT=` для локалки. Пояснение: защита сетевая (Tailscale), это API-токены сервисов.
  - `README.md`: секция «MCP-слой (этап 2)» — каждое направление как remote MCP по HTTP за поддоменом `mcp-<svc>.dashboard.example.com`, таблица поддоменов, ссылки на `docs/mcp/CONVENTIONS.md` и `docs/adr/0007-mcp-integration-topology.md`.
- **Context:** `.env.example` (текущая структура секций), `README.md` (стиль разделов/таблиц), `docs/mcp/CONVENTIONS.md` (создан в Task 1 — на него ссылаемся).
- **Verify:** `grep -q 'MCP layer' .env.example && grep -qi 'mcp-' README.md` — обе строки найдены.

### Task 3: Validation

- **Files:** —
- **Depends on:** all
- **Scope:** S
- **What:** Проверить, что репозиторий-compose остаётся валидным и артефакты на месте.
- **Context:** —
- **Verify:** `docker compose config -q` — без ошибок; `test -f services/_mcp/Dockerfile && test -f docs/mcp/CONVENTIONS.md` — файлы есть.

## Execution

- **Mode:** inline
- **Parallel:** false
- **Reasoning:** Две небольшие задачи; Task 2 ссылается на файлы, созданные в Task 1, поэтому строго последовательно.
- **Order:**
  Task 1 → Task 2 → Task 3

## Verification

- Есть `docs/mcp/CONVENTIONS.md` — документированный образец, на который ссылаются сервисные issues (#12–#17).
- Переиспользуемый bridge-Dockerfile (`services/_mcp/Dockerfile`) собирается и параметризуется через `MCP_PKG`.
- Зафиксированы: размещение, транспорт (native vs bridge), сеть+роутинг через Dokploy UI без Traefik-labels, неймспейс секретов `<SVC>_MCP_TOKEN`, healthcheck/лимиты.
- `.env.example` и `README.md` отражают MCP-слой.
- `docker compose config -q` проходит.

## Materials

- Issue #10: https://github.com/prineycom/svc-personal-dashboard/issues/10
- Epic #9: https://github.com/prineycom/svc-personal-dashboard/issues/9
- ADR 0007: `docs/adr/0007-mcp-integration-topology.md`
- supergateway: https://github.com/supercorp-ai/supergateway
