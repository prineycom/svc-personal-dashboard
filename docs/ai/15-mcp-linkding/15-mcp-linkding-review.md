# Code Review: 15-mcp-linkding

## Summary

### Context and goal

Добавлен нативный MCP-контейнер `mcp-linkding` (`ghcr.io/chickenzord/linkding-mcp:v0.1.6`) в корневой `docker-compose.yml` как MCP Endpoint для Linkding (issue #15, epic #9). Первый MCP-контейнер в Blueprint.

### Key code areas for review

1. **`docker-compose.yml:453-488` (`mcp-linkding`)** — соответствие шаблону §6 «Native (Firefly III)» конвенции: образ, порт, сети, лимиты.
2. **`docs/mcp/CONVENTIONS.md:44-46`** — фиксация кастомного пути `/mcp/v1` и URL для Hermes.

### Complex decisions

1. **`condition: service_started`** (`docker-compose.yml:461`) — у `linkding` нет healthcheck, поэтому `service_healthy` невозможен; `service_started` — единственный валидный вариант.
2. **Отсутствие healthcheck** (`docker-compose.yml:471`) — минимальный Go-образ без shell/`wget` и без health-эндпоинта; повторяет прецедент `vikunja`.
3. **`BIND_ADDR: ":8000"`** — переопределение дефолта образа `:8080` ради единого порта `8000` по конвенции.

### Questions for the reviewer

1. Подтверждена ли совместимость кастомного REST-протокола образа (`/mcp/v1/*`) с MCP-клиентом Hermes? Проверяется на verify (ops-шаг вне репозитория).

### Risks and impact

- Образ отдаёт `/mcp/v1/*`, а не стандартный streamable-HTTP `/mcp` — если Hermes ждёт стандартный транспорт, потребуется мост/обёртка. Зафиксировано в задаче как риск.
- Пустой `LINKDING_MCP_TOKEN` → контейнер стартует, но вызовы к Linkding API возвращают ошибку авторизации.

### Tests and manual checks

**Auto-tests:**

- N/A — инфраструктурный compose, тулчейна тестов нет.

**Manual scenarios:**

1. `docker compose config -q` → без ошибок (выполнено ✅).
2. `LINKDING_MCP_PORT=8100 docker compose up -d linkding mcp-linkding` → оба running.
3. `curl -s -X POST http://localhost:8100/mcp/v1/tools/list` → `search_bookmarks`, `create_bookmark`, `get_tags`.
4. Регистрация `https://mcp-linkding.dashboard.example.com/mcp/v1` в Hermes; сохранить/найти закладку.

### Out of scope

- Фактическая регистрация в Hermes и AI-summary/теги — на стороне Hermes, вне репозитория.
- Traefik-роутинг поддомена — задаётся в Dokploy UI, не в compose.

## Commits

| Hash    | Description                                                  |
| ------- | ------------------------------------------------------------ |
| fcb2767 | #15 feat(15-mcp-linkding): add linkding MCP native container |
| 00943ea | #15 docs(15-mcp-linkding): document linkding MCP endpoint path |

## Changed Files

| File                    | +/-  | Description                                              |
| ----------------------- | ---- | -------------------------------------------------------- |
| docker-compose.yml      | +36  | Сервис `mcp-linkding` (native `:v0.1.6`)                 |
| .env.example            | +2   | Комментарий к `LINKDING_MCP_TOKEN`                       |
| docs/mcp/CONVENTIONS.md | +3   | Заметка §3 о пути `/mcp/v1` и URL для Hermes             |

## Issues Found

Статический review был «чист», но **runtime-верификация** (запуск контейнера на ARM64) вскрыла два дефекта:

| Severity | Score | Category      | Где                  | Описание                                                                 |
| -------- | ----- | ------------- | -------------------- | ------------------------------------------------------------------------ |
| Critical | 90    | compatibility | docker-compose.yml   | Официальный образ хардкодит `GOARCH=amd64` → arm64-вариант = x86-64 бинарь, `exec format error` на Pi |
| Important| 70    | correctness   | docker-compose.yml   | Тег `:v0.1.6` не существует на ghcr.io (образы публикуются без `v`: `0.1.6`) |
| Minor    | 40    | docs          | CONVENTIONS.md       | Заявленный путь `/mcp/v1/*` неверен — сервер отдаёт стандартный MCP streamable-HTTP на `/mcp` |

## Fixed Issues

| Issue                         | Commit    | Description                                                        |
| ----------------------------- | --------- | ----------------------------------------------------------------- |
| arm64-образ не исполняется    | `0d256e0` | Сборка из исходников под нативную арку (`services/linkding/mcp/Dockerfile`) |
| Неверный тег образа           | `0d256e0` | Переход на `build:`; upstream пиннится тегом `v0.1.6` в build-arg  |
| Неверный путь эндпоинта в доке | `0d256e0` | Исправлено на стандартный streamable-HTTP `/mcp` в CONVENTIONS/ADR |

## Skipped Issues

**All found issues were fixed.**

## Runtime verification (на ARM64 Pi)

- `docker build services/linkding/mcp` → образ собран; `file` бинаря → `ELF ... ARM aarch64` ✅
- `docker compose build mcp-linkding` → образ собран через compose ✅
- Запуск + MCP-хендшейк `POST /mcp {initialize}` → `200`, `Mcp-Session-Id`, `serverInfo: linkding-mcp v0.1.6` ✅
- `tools/list` в сессии → `search_bookmarks`, `create_bookmark`, `get_tags` ✅

## Recommendations

- На реальном деплое подтвердить connect Hermes → `https://mcp-linkding.dashboard.example.com/mcp` и end-to-end сохранение/поиск закладки (с валидным `LINKDING_MCP_TOKEN`).
- Сгенерировать `LINKDING_MCP_TOKEN` в UI Linkding и прописать в Dokploy → Environment перед деплоем.
- Рассмотреть upstream-иссью chickenzord/linkding-mcp о хардкоде `GOARCH=amd64`; при фиксе можно вернуться на официальный образ.
