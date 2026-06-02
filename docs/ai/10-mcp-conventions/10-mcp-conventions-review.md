# Code Review: 10-mcp-conventions

## Summary

### Context and goal

Issue #10 фиксирует соглашения MCP-слоя (этап 2): переиспользуемый stdio→HTTP
bridge-образ + центральный документ конвенций, на который опираются сервисные
issues #12–#17. Кода почти нет — инфраструктура и документация.

### Key code areas for review

1. **`services/_mcp/Dockerfile`** — единственный исполняемый артефакт; его
   копируют Vikunja (#12) и Wger (#14). Корректность флагов supergateway
   критична.
2. **`docs/mcp/CONVENTIONS.md`** — источник истины для всех сервисных задач.

### Complex decisions

1. **Роутинг через Dokploy UI, не Traefik-labels** (`docs/mcp/CONVENTIONS.md` §3) —
   расходится с формулировкой issue #10, но соответствует фактической конвенции
   репо (revert-коммит `00f26e5`).
2. **supergateway для bridge, native-образ для Firefly/Linkding** — мост не
   универсален, применяется выборочно.

### Questions for the reviewer

1. Версии пинов (`SUPERGATEWAY_VERSION=3.4.0`, `vikunja-mcp@0.2.0`) — актуальны?
   Финализируются в #12/#14.

### Risks and impact

- Рантайм bridge-контейнера не проверялся (собран, но не запущен) — реальный
  старт supergateway проверяется в #12.
- Health-путь в native-сниппете Firefly задан как `/healthz` для примера; точный
  путь образа сверяется в #13.

### Tests and manual checks

**Auto-tests:** N/A (compose-репо без тест-раннера).

**Manual scenarios:**
1. `docker build --build-arg MCP_PKG=@democratize-technology/vikunja-mcp@0.2.0 services/_mcp` → образ собирается ✅
2. `docker compose config -q` → exit 0 ✅

### Out of scope

- Реальные MCP-контейнеры в `docker-compose.yml` — это #12–#17.
- Свои FastMCP (BeaverHabits, OpenTickly).

## Commits

| Hash | Description |
|------|-------------|
| 1de94c2 | docs: add implementation plan |
| d056c3d | feat: add reusable MCP bridge image and conventions doc |
| 8f47a3a | docs: surface MCP layer in .env.example and README |
| 2aa87a8 | docs: add execution report |
| 1bf5140 | fix: document /mcp endpoint path in MCP conventions |

## Changed Files

| File | +/- | Description |
|------|-----|-------------|
| `services/_mcp/Dockerfile` | +46 | supergateway bridge-образ |
| `services/_mcp/README.md` | +62 | как добавлять bridged-MCP |
| `docs/mcp/CONVENTIONS.md` | +145 | центральный документ конвенций |
| `.env.example` | +22 | MCP-токены + локальные порты |
| `README.md` | +21 | подраздел MCP layer |

## Issues Found

| Severity | Score | Category | File:line | Description |
|----------|-------|----------|-----------|-------------|
| Important | 60 | correctness/docs | docs/mcp/CONVENTIONS.md §3 | Не указан путь `/mcp` streamable-HTTP эндпоинта — Hermes-URL в #12/#14 был бы неполным |

## Fixed Issues

| Issue | Commit | Description |
|-------|--------|-------------|
| Отсутствовал путь `/mcp` эндпоинта | `1bf5140` | Добавлен путь `/mcp` (+ `/healthz`) и полный Hermes-URL в CONVENTIONS и bridge README |

## Skipped Issues

| Issue | Reason |
|-------|--------|
| Рантайм-проверка supergateway | Вне скоупа #10 — проверяется в #12 (первый реальный bridge) |
| Точный health-путь native-образа Firefly | Вне скоупа #10 — сверяется в #13 |

## Recommendations

- В #12 запустить bridge-контейнер и подтвердить ответ на `/mcp` и `/healthz`.
- При финализации #12/#14 сверить пины `SUPERGATEWAY_VERSION` и версию MCP-пакета.
