# Report: 13-firefly-mcp-native

**Plan:** docs/ai/13-firefly-mcp-native/13-firefly-mcp-native-plan.md
**Mode:** inline
**Status:** ⚠️ partial

## Tasks

| #   | Task                                      | Status   | Commit    | Concerns  |
| --- | ----------------------------------------- | -------- | --------- | --------- |
| 1   | Добавить сервис mcp-firefly               | ✅ DONE  | `7df3f00` | —         |
| 2   | Поправить сниппет Firefly в CONVENTIONS.md | ✅ DONE  | `5265bb4` | —         |
| 3   | Validation                                | ❌ FAILED | —         | see below |

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

## Changes summary

| File                     | Action   | Description                                                                  |
| ------------------------ | -------- | ---------------------------------------------------------------------------- |
| docker-compose.yml       | modified | Добавлен сервис `mcp-firefly` (native образ, `@sha256:`, health `/openapi.json`) |
| .env.example             | modified | Комментарий: `FIREFLY_MCP_TOKEN` — Firefly Personal Access Token             |
| docs/mcp/CONVENTIONS.md  | modified | §6 Firefly: пин по дайджесту, health `/openapi.json`; §3: примечание про `/sse` |

## Commits

- `7df3f00` #13 feat(13-firefly-mcp-native): add mcp-firefly native HTTP service
- `5265bb4` #13 docs(13-firefly-mcp-native): correct firefly native snippet
