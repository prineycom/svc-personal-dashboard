# Report: 13-firefly-mcp-native

**Plan:** docs/ai/13-firefly-mcp-native/13-firefly-mcp-native-plan.md
**Mode:** inline
**Status:** ✅ complete (после смены подхода native → bridge)

## Tasks

| #   | Task                                       | Status   | Commit    | Concerns          |
| --- | ------------------------------------------ | -------- | --------- | ----------------- |
| 1   | Добавить сервис mcp-firefly (native)       | ↩️ заменён | `7df3f00` | образ amd64-only  |
| 2   | Поправить сниппет Firefly в CONVENTIONS.md | ↩️ заменён | `5265bb4` | пересмотрен        |
| 3   | Validation                                 | ❌→✅     | —         | см. Resolution    |
| 4   | Перевод mcp-firefly на bridge              | ✅ DONE  | `d472341` | —                 |
| 5   | Обновление CONVENTIONS/ADR/CONTEXT/_mcp     | ✅ DONE  | `a573e25` | —                 |

## Validation

- `docker compose config -q` ✅ — конфиг валиден, `mcp-firefly` присутствует, образ пиннится по `@sha256:`.
- `docker pull …@sha256:46dce54…` ✅ — образ скачивается.
- `docker run …` на arm64 ❌ — **`exec format error`**. Образ существует только под `linux/amd64` (single-arch `manifest.v2`, без manifest list / arm64-варианта). На Raspberry Pi 5 (arm64 — целевой хост Blueprint) контейнер не стартует.
- `curl /openapi.json` → HTTP 000 (контейнер не поднялся).
- `curl /sse` → недоступно (контейнер не поднялся).

## Blocked

### Task 3: Validation — образ не arm64

**Reason:** `ghcr.io/fabianonetto/mcp-server-firefly-iii` публикуется только под `linux/amd64`. На целевом arm64-хосте (Pi 5) даёт `exec format error`. Это противоречит требованию Blueprint «Pi 5 / ARM64 совместим» (CONTEXT.md, ADR 0007 — native-образы запускаются напрямую).
**Impact:** Сервис `mcp-firefly` поднимется на amd64-деплое, но не на Pi. Решение об архитектуре подключения требует выбора пользователя.

**Варианты ремедиации:**
1. **Bridge через `services/_mcp/`.** Пакет `mcp-server-firefly-iii@3.0.0` опубликован в npm; `node:22-alpine` мультиарх → bridge собирается и работает на arm64. Транспорт станет streamable-HTTP `/mcp` (как у Vikunja/Wger), а не `/sse`. Firefly переезжает из native- в bridge-кейс — это разворачивает DD-1, ADR 0007 и таблицу транспортов в CONVENTIONS.
2. **Свой arm64-образ.** Собрать из исходников upstream (в репозитории есть Dockerfile) и публиковать свой multi-arch образ. Поддержка ложится на нас.
3. **QEMU/binfmt-эмуляция amd64 на Pi.** Медленно и хрупко для постоянного сервиса — не рекомендуется.
4. **Деплой не на Pi.** Если целевой хост x86-64 — текущий native-вариант рабочий, блокер снимается.

Рекомендация: вариант 1 (bridge) — переиспользует готовый `services/_mcp/`, остаётся на официальном пакете, работает на arm64.

## Resolution (native → bridge)

Решение пользователя по блокеру — вариант 1 (bridge). Перед переходом bridge
**проверен на arm64**:

- `docker build --build-arg MCP_PKG=mcp-server-firefly-iii@3.0.0 ./services/_mcp` ✅ — собирается на Pi.
- `GET /healthz` ✅ HTTP 200.
- `POST /mcp` (initialize) ✅ HTTP 200, `text/event-stream`; дочерний процесс ответил `serverInfo: mcp-server-firefly-iii 3.0.0`, capabilities `tools`.
- `docker compose config -q` ✅ — конфиг с `build:` валиден.

`mcp-firefly` теперь bridge: `build: ./services/_mcp` + `MCP_PKG: mcp-server-firefly-iii@3.0.0`,
env `FIREFLY_URL`/`FIREFLY_TOKEN` (без `PORT` — пакет остаётся stdio), health `/healthz`.
URL для Hermes — `https://mcp-firefly.dashboard.example.com/mcp`.

Изменения в native-коммитах (`7df3f00`, `5265bb4`) перекрыты, но оставлены в
истории как след принятого и отменённого решения.

## Финальная валидация

- `docker compose config -q` ✅
- bridge build (arm64) ✅
- `GET /healthz` ✅ 200
- `POST /mcp` initialize ✅ 200, `text/event-stream`

## Changes summary

| File                                        | Action   | Description                                                                  |
| ------------------------------------------- | -------- | ---------------------------------------------------------------------------- |
| docker-compose.yml                          | modified | Сервис `mcp-firefly` — bridge (`services/_mcp`, `MCP_PKG`), health `/healthz` |
| .env.example                                | modified | Комментарий: `FIREFLY_MCP_TOKEN` — Firefly Personal Access Token             |
| docs/mcp/CONVENTIONS.md                     | modified | Firefly → bridge: транспортная таблица, сноска про amd64, §6 сниппет          |
| services/_mcp/README.md                     | modified | Таблица «who uses it»: Firefly → bridge; критерий native/bridge уточнён       |
| services/_mcp/Dockerfile                    | modified | Комментарий: Firefly в bridge (образ amd64-only)                             |
| docs/adr/0007-mcp-integration-topology.md   | modified | Решение #2 и таблица: Firefly → bridge; Update (2026-06-02, #13)             |
| CONTEXT.md                                  | modified | Глоссарий Bridge + решения «Топология»/«Финансы»: Firefly → bridge           |

## Commits

- `7df3f00` #13 feat(13-firefly-mcp-native): add mcp-firefly native HTTP service _(перекрыт)_
- `5265bb4` #13 docs(13-firefly-mcp-native): correct firefly native snippet _(перекрыт)_
- `c05d6e1` #13 docs(13-firefly-mcp-native): add execution report
- `d472341` #13 fix(13-firefly-mcp-native): bridge mcp-firefly for arm64 (image is amd64-only)
- `a573e25` #13 docs(13-firefly-mcp-native): record firefly bridge pivot in conventions, ADR, context
