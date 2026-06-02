# Code Review: 14-mcp-wger-supergateway

## Summary

### Context and goal

Подключение направления «здоровье» (Wger) к Hermes: stdio-only пакет `@juxsta/wger-mcp` оборачивается общим bridge-образом `services/_mcp` (supergateway → streamable-HTTP) и направляется на внутренний wger-инстанс. Реализация — один сервис `mcp-wger` в корневом `docker-compose.yml`.

### Key code areas for review

1. **`docker-compose.yml` `mcp-wger`** — bridge-сервис: build-arg `MCP_PKG`, маппинг секрета, upstream, сеть, healthcheck.

### Complex decisions

1. **service_healthy vs service_started** (`docker-compose.yml` `mcp-wger.depends_on`) — выбран `service_healthy`: bridge стартует только после готовности `wger-nginx`. Альтернатива `service_started` отклонена в ревью в пользу строгого гейта.
2. **Upstream `http://wger-nginx/api/v2`** — обращение по внутренней сети `internal`, не к публичному `wger.de`; согласовано с таблицей хостов `docs/mcp/CONVENTIONS.md` §3.

### Questions for the reviewer

1. Версия `@juxsta/wger-mcp@1.1.1` зафиксирована вручную — подтвердить политику бампа (как для supergateway в `services/_mcp/Dockerfile`).

### Risks and impact

- Сборка образа и round-trip из Hermes не выполнялись локально (нужен реальный `WGER_MCP_TOKEN` и хост) — проверяются при деплое по runbook в отчёте `/do`.
- `ports: ${WGER_MCP_PORT:-}:8000` пуст на Dokploy — публичный порт не открывается, доступ только через Traefik/Tailscale (как у соседних сервисов).

### Tests and manual checks

**Auto-tests:**

- Нет тест-сьюта (инфраструктурный YAML-репо). Валидатор — `docker compose config -q`.

**Manual scenarios:**

1. `WGER_MCP_PORT=8080 docker compose up -d --build mcp-wger` → контейнер `healthy`.
2. `curl -fsS http://localhost:8080/healthz` → `ok`; `curl -fsS http://localhost:8080/mcp` → streamable-HTTP.
3. Round-trip из Hermes: чтение/создание тренировки → данные в self-hosted wger.

### Out of scope

- Регистрация поддомена в Dokploy UI и эндпоинта в Hermes (внешние UI).
- Изменения `services/_mcp/Dockerfile` и общего `.env.example`-неймспейса.

## Commits

| Hash    | Description                                          |
| ------- | --------------------------------------------------- |
| 0fd6104 | feat(14-mcp-wger-supergateway): add mcp-wger bridge service |
| 24e7442 | fix(14-mcp-wger-supergateway): fix 1 review issue    |

## Changed Files

| File                | +/-  | Description                                             |
| ------------------- | ---- | ------------------------------------------------------- |
| `docker-compose.yml` | +43  | Bridge-сервис `mcp-wger` (supergateway + `@juxsta/wger-mcp@1.1.1`) |

## Issues Found

| Severity | Score | Category   | File:line                          | Description                                                                 |
| -------- | ----- | ---------- | ---------------------------------- | --------------------------------------------------------------------------- |
| Minor    | 30    | robustness | `docker-compose.yml` `mcp-wger.depends_on` | `condition: service_started` не гейтит bridge по готовности wger-nginx |

## Fixed Issues

| Issue                                   | Commit    | Description                                          |
| --------------------------------------- | --------- | --------------------------------------------------- |
| depends_on condition (service_started) | `24e7442` | Заменено на `condition: service_healthy` — bridge ждёт готовности wger-nginx |

## Skipped Issues

**All found issues were fixed.**

## Recommendations

- При деплое выполнить runbook из отчёта `/do`: сборка/health-проверка контейнера, регистрация в Dokploy и Hermes, round-trip создания тренировки.
- Зафиксировать единую политику бампа версий MCP-пакетов (`@juxsta/wger-mcp`, supergateway) — например, в `services/_mcp/README.md`.
