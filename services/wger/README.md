# Wger — сервис здоровья и его MCP

Wger (gym + питание) как направление Dashboard плюс MCP-эндпоинт, через который
Hermes управляет тренировками. Архитектура слоя — [ADR 0007](../../docs/adr/0007-mcp-integration-topology.md),
общие конвенции MCP — [docs/mcp/CONVENTIONS.md](../../docs/mcp/CONVENTIONS.md),
термины (`MCP Endpoint`, `Bridge`) — [CONTEXT.md](../../CONTEXT.md).

## Состав

Сервис wger — 4 контейнера в корневом `docker-compose.yml`:

| Контейнер           | Образ              | Роль                                  |
| ------------------- | ------------------ | ------------------------------------- |
| `wger-web`          | `wger/server:2.5`  | Django-приложение (API + UI) на `:8000` |
| `wger-nginx`        | `nginx:stable`     | Статика/медиа + прокси на `wger-web`, публичный порт `:80` |
| `wger-celery-worker`| `wger/server:2.5`  | Фоновые задачи (синк упражнений/ингредиентов) |
| `wger-celery-beat`  | `wger/server:2.5`  | Планировщик Celery                    |

MCP добавляет пятый контейнер:

| Контейнер  | Сборка                         | Роль                                            |
| ---------- | ------------------------------ | ----------------------------------------------- |
| `mcp-wger` | `services/_mcp` (supergateway) | Оборачивает stdio-`@juxsta/wger-mcp` в HTTP `/mcp` |

`mcp-wger` — случай **Bridge**: у пакета нет нативного HTTP-образа, поэтому общий
образ `services/_mcp` оборачивает его stdio в streamable-HTTP через supergateway.
Internal-маршрут: `mcp-wger` → `wger-nginx` → `wger-web`. Наружу (через Tailscale)
ходит только Hermes → `mcp-wger`.

## Инструменты MCP (9)

Проверено на `@juxsta/wger-mcp@1.1.1` (сервер self-репортит `0.1.0`; число
инструментов в README пакета — 12 — не совпадает с реальностью):

`list_categories`, `list_muscles`, `list_equipment`, `search_exercises`,
`get_exercise_details`, `create_workout`, `add_exercise_to_routine`,
`get_user_routines`, `diagnose`.

## Переменные окружения

Задаются в **корневом `.env`** (не в этой папке). Плейсхолдеры — в корневом
[`.env.example`](../../.env.example).

### Сам сервис wger (префикс `WGER_*`)

Полный список — в корневом `.env.example`, секция «Wger». Ключевые:

| Переменная                  | Назначение                                          | Пример                         |
| --------------------------- | --------------------------------------------------- | ------------------------------ |
| `WGER_SECRET_KEY`           | Django secret (50 случайных символов)               | `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `WGER_SIGNING_KEY`          | Django signing key (50 символов)                    | то же                          |
| `WGER_DJANGO_DEBUG`         | Должно быть `False`, иначе пустой `wger_static`      | `False`                        |
| `WGER_CSRF_TRUSTED_ORIGINS` | Публичный домен, иначе логин 403                    | `https://fitness.dashboard.example.com` |
| `WGER_DJANGO_DB_PASSWORD`   | Пароль к shared PostgreSQL                           | `${POSTGRES_PASSWORD}`         |
| `WGER_PORT`                 | Локальный хост-порт nginx (на Dokploy пусто)         | `8001`                         |

### MCP-эндпоинт (`mcp-wger`)

| Переменная                | Где задаётся                | Назначение                                                        |
| ------------------------- | --------------------------- | ----------------------------------------------------------------- |
| `WGER_MCP_TOKEN`          | корневой `.env`             | API-ключ wger. Маппится в compose на `WGER_API_KEY` образа.       |
| `WGER_MCP_PORT`           | корневой `.env` (опц.)      | Локальный хост-порт для теста. На Dokploy — пусто.                 |
| `WGER_API_URL`            | **хардкод в `docker-compose.yml`** | `http://wger-nginx/api/v2` — internal upstream, не env. Менять не нужно. |

> Конвенция неймспейса: токен живёт под `WGER_MCP_TOKEN`, а в `environment:`
> блока `mcp-wger` мапится на имя, которое ждёт образ (`WGER_API_KEY`). См.
> `docs/mcp/CONVENTIONS.md` §4.

Альтернатива API-ключу — логин/пароль (`WGER_USERNAME` + `WGER_PASSWORD` в
образе). В Blueprint используется только API-ключ — он не привязан к смене пароля.

## Где взять `WGER_MCP_TOKEN`

1. Откройте UI вашего self-hosted wger (например `https://fitness.dashboard.example.com`).
2. Войдите под аккаунтом, от имени которого Hermes будет вести тренировки.
3. Меню пользователя → раздел **API** (путь `/en/user/api`).
4. Скопируйте **API key** и впишите его в корневой `.env` как `WGER_MCP_TOKEN=<key>`.

Токен даёт доступ к данным только этого пользователя (`create_workout`,
`get_user_routines` и т.д.). Поиск упражнений (`search_exercises`,
`list_*`) работает и без токена.

## Локальная проверка

Собрать и запустить только bridge (зависит от `wger-nginx` по
`condition: service_healthy`, поэтому поднимется и стек wger):

```bash
# из корня репозитория
WGER_MCP_PORT=18080 docker compose up -d --build mcp-wger
```

Проверить эндпоинты:

```bash
# health — должно вернуть "ok"
curl -fsS http://localhost:18080/healthz

# MCP initialize — должен вернуть serverInfo (streamable-HTTP, SSE)
curl -sS -X POST http://localhost:18080/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"cli","version":"0"}}}'

# список инструментов — ожидается 9
curl -sS -X POST http://localhost:18080/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# проверка конфигурации внутри сервера (видит ли он URL и токен)
curl -sS -X POST http://localhost:18080/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"diagnose","arguments":{}}}'
```

Только статическая валидация compose без запуска:

```bash
docker compose config -q          # exit 0 — конфиг валиден
```

## Деплой (Dokploy)

1. Впишите в окружение Dokploy `WGER_MCP_TOKEN` (и остальные `WGER_*`).
   `WGER_MCP_PORT` оставьте пустым.
2. Задеплойте стек — поднимется контейнер `mcp-wger`.
3. В Dokploy UI создайте домен **`mcp-wger.dashboard.example.com`** → порт
   контейнера **`8000`**. Traefik-labels в compose **не добавляйте** — источник
   роутинга Dokploy UI.
4. Доступ снаружи закрыт Tailscale; собственной авторизации у эндпоинта нет.

## Регистрация в Hermes и round-trip

1. Зарегистрируйте в Hermes MCP-эндпоинт:
   `https://mcp-wger.dashboard.example.com/mcp`.
2. Проверьте сквозной сценарий из Hermes:
   - прочитать тренировки (`get_user_routines`);
   - создать тренировку (`create_workout`);
   - убедиться, что запись появилась в UI **self-hosted** wger (не на `wger.de`).
   Это подтверждает, что `WGER_API_URL` указывает на внутренний инстанс, а
   `WGER_MCP_TOKEN` валиден.

## Траблшутинг

| Симптом                                   | Причина / решение                                              |
| ----------------------------------------- | --------------------------------------------------------------- |
| `/healthz` молчит, контейнер не `healthy` | `mcp-wger` ждёт `wger-nginx` (`service_healthy`); проверьте стек wger. |
| `diagnose` показывает `apiUrl: …wger.de`  | Не подхватился хардкод; сверьте блок `mcp-wger.environment` в compose. |
| Tool-вызовы возвращают 401/403            | Невалидный `WGER_MCP_TOKEN` — перегенерируйте ключ в UI wger.   |
| Данные уходят на `wger.de`                | `WGER_API_URL` указывает не на `wger-nginx`; проверьте compose. |
| `npm install` падает на сборке            | Сетевой доступ к npm на хосте; пакет ставится на этапе build.   |

## Ссылки

- Пакет: [Juxsta/wger-mcp](https://github.com/Juxsta/wger-mcp) · [@juxsta/wger-mcp (npm)](https://www.npmjs.com/package/@juxsta/wger-mcp)
- Bridge-образ: [`services/_mcp/README.md`](../_mcp/README.md)
- nginx-конфиг wger: [`services/wger/nginx.conf`](nginx.conf)
- API wger: [wger REST API docs](https://wger.de/en/software/api)
