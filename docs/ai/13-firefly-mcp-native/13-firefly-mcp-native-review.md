# Code Review: 13-firefly-mcp-native

## Summary

### Context and goal

Подключение Firefly III к Hermes через MCP. Изначально — нативный официальный образ (issue #13, ADR 0007), но образ оказался `linux/amd64`-only и не идёт на Pi (arm64). Подключение переведено на bridge: npm-пакет `mcp-server-firefly-iii@3.0.0` оборачивается общим `services/_mcp` (supergateway) в streamable-HTTP.

### Key code areas for review

1. **`docker-compose.yml:204` (`mcp-firefly`)** — bridge-сервис: `build: ./services/_mcp` + `MCP_PKG`, env `FIREFLY_URL`/`FIREFLY_TOKEN`, health `/healthz`, сети `internal`+`dokploy-network`.
2. **`docs/mcp/CONVENTIONS.md` §1, §6** — критерий native/bridge уточнён (нужна сборка под целевую арку); Firefly перенесён в bridge.
3. **`docs/adr/0007-mcp-integration-topology.md`** — решение #2 и таблица обновлены, добавлен Update (2026-06-02, #13).

### Complex decisions

1. **native → bridge** (`docker-compose.yml:204`) — официальный образ amd64-only; npm-пакет мультиарх. Trade-off: теряем «официальный образ», получаем arm64-совместимость и единый bridge-паттерн. Эндпоинт Hermes меняется с `/sse` на `/mcp`.
2. **`depends_on: service_started`** — у `firefly-app` нет healthcheck, поэтому `service_healthy` завис бы; `service_started` корректен.
3. **Без `PORT` в env** — пакет остаётся в stdio-режиме, HTTP даёт supergateway; задание `PORT` переключило бы пакет в собственный HTTP и сломало мост.

### Questions for the reviewer

1. Лимит `memory: 128M` для Node+supergateway+firefly-MCP — достаточно ли под нагрузкой? (соответствует конвенции, но не замерялось под трафиком).
2. Пин `mcp-server-firefly-iii@3.0.0` — следить за обновлениями npm-пакета вручную (semver-пин, не дайджест).

### Risks and impact

- E2E через Hermes/Dokploy/Tailscale не проверялся — только локальный bridge на arm64. Регистрация поддомена и Hermes — ручные ops-шаги.
- При недоступном `firefly-app` контейнер поднимется, но tool-вызовы к Firefly вернут ошибку (ожидаемо).
- Issue #13 в GitHub всё ещё описывает native-подход — текст расходится с реализацией (комментарий не оставлен).

### Tests and manual checks

**Auto-tests:** в infra-репозитории нет; проверка — `docker compose config -q`.

**Manual scenarios (выполнены на arm64):**
1. `docker build --build-arg MCP_PKG=mcp-server-firefly-iii@3.0.0 ./services/_mcp` → собирается.
2. `GET /healthz` → HTTP 200.
3. `POST /mcp` (initialize) → HTTP 200, `text/event-stream`, `serverInfo: mcp-server-firefly-iii 3.0.0`, capabilities `tools`.
4. `docker compose config -q` → exit 0.

### Out of scope

- Генерация Personal Access Token в UI Firefly.
- Регистрация поддомена `mcp-firefly.dashboard.example.com` в Dokploy UI.
- Регистрация эндпоинта в Hermes.
- Реальный деплой и проверка через Tailscale.

## Commits

| Hash    | Description                                                              |
| ------- | ------------------------------------------------------------------------ |
| 7df3f00 | feat: add mcp-firefly native HTTP service _(перекрыт)_                    |
| 5265bb4 | docs: correct firefly native snippet _(перекрыт)_                        |
| c05d6e1 | docs: add execution report                                               |
| d472341 | fix: bridge mcp-firefly for arm64 (image is amd64-only)                  |
| a573e25 | docs: record firefly bridge pivot in conventions, ADR, context          |
| b71b0e2 | docs: update report with bridge resolution                              |
| 62444e1 | fix: fix 1 review issue                                                  |

## Changed Files

| File                                      | +/-     | Description                                          |
| ----------------------------------------- | ------- | ---------------------------------------------------- |
| docker-compose.yml                        | +41/-0  | Сервис `mcp-firefly` (bridge)                        |
| docs/mcp/CONVENTIONS.md                   | +37/-12 | Firefly → bridge; критерий native/bridge; сноска     |
| docs/adr/0007-mcp-integration-topology.md | +12/-2  | Решение #2, таблица, Update (#13)                    |
| CONTEXT.md                                | +3/-3   | Глоссарий Bridge + решения «Топология»/«Финансы»     |
| services/_mcp/README.md                   | +5/-4   | Таблица «who uses it»; критерий native/bridge        |
| services/_mcp/Dockerfile                  | +5/-3   | Комментарий: Firefly в bridge                        |
| .env.example                              | +1/-0   | Блочный комментарий про Firefly PAT                  |

## Issues Found

| Severity | Score | Category    | File:line          | Description                                                              |
| -------- | ----- | ----------- | ------------------ | ------------------------------------------------------------------------ |
| Minor    | 30    | portability | .env.example:116   | Inline-комментарий после `FIREFLY_MCP_TOKEN=` мог попасть в значение у строгих dotenv-парсеров |

## Fixed Issues

| Issue                                | Commit    | Description                                              |
| ------------------------------------ | --------- | ------------------------------------------------------- |
| Inline-комментарий в .env.example    | `62444e1` | Перенесён в блочный комментарий над ключом, как в файле  |

## Skipped Issues

**All found issues were fixed.**

## Recommendations

- Перед мержем оставить комментарий в issue #13 о переходе native → bridge (arm64), чтобы тикет не расходился с реализацией.
- При следующем native-образе (Linkding, #15) — заранее проверять multi-arch манифест: `docker buildx imagetools inspect <image>`.
- Отслеживать релизы npm `mcp-server-firefly-iii` (пин semver `@3.0.0`).
- Проверить E2E через Hermes после деплоя и регистрации поддомена в Dokploy.
