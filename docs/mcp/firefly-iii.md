# Firefly III MCP — настройка

Подключение финансов (Firefly III) к ИИ-агенту **Hermes** через MCP.
Общие правила MCP-слоя — [`CONVENTIONS.md`](CONVENTIONS.md), решение —
[ADR 0007](../adr/0007-mcp-integration-topology.md).

## Что это

Контейнер `mcp-firefly` даёт Hermes доступ к Firefly III API (66 инструментов:
счета, транзакции, бюджеты, правила, валюты и т.д.).

**Транспорт — bridge, не native.** Официальный образ
`ghcr.io/fabianonetto/mcp-server-firefly-iii` собран только под `linux/amd64`
и на Pi (arm64) падает с `exec format error`. npm-пакет `mcp-server-firefly-iii`
мультиарх, поэтому оборачивается общим мостом [`services/_mcp`](../../services/_mcp/)
(supergateway): stdio → streamable-HTTP. Эндпоинт для Hermes —
`https://mcp-firefly.dashboard.example.com/mcp`, health — `/healthz`.

```
Hermes ──HTTPS /mcp──► mcp-firefly (supergateway) ──stdio──► mcp-server-firefly-iii
                                                   ──HTTP──► firefly-app:8080 (Firefly API)
```

## Переменные окружения

Всё в корневом `.env` (см. блок «MCP layer» в [`.env.example`](../../.env.example)).

| Переменная          | Обяз. | Назначение | Куда идёт |
| ------------------- | :---: | ---------- | --------- |
| `FIREFLY_MCP_TOKEN` |  ✅   | Firefly **Personal Access Token** — им MCP ходит в Firefly API | compose мапит в `FIREFLY_TOKEN` контейнера |
| `FIREFLY_MCP_PORT`  |  —    | host-порт только для локального теста; на Dokploy пусто | `ports: ${FIREFLY_MCP_PORT:-}:8000` |

`FIREFLY_URL` **не** в `.env` — он зашит в `docker-compose.yml` как
`http://firefly-app:8080` (внутренний хост по сети `internal`, не публичный URL).

Имя `FIREFLY_MCP_TOKEN` (неймспейс `.env`) → `FIREFLY_TOKEN` (имя, которое ждёт
пакет) — маппинг в `docker-compose.yml`:

```yaml
    environment:
      FIREFLY_URL: http://firefly-app:8080
      FIREFLY_TOKEN: ${FIREFLY_MCP_TOKEN:-}
```

## Настройка по шагам

### 1. Получить Personal Access Token в Firefly III

1. Открыть Firefly III (`https://finance.dashboard.example.com`).
2. **⚙ Options → Profile → вкладка «OAuth»**.
3. Блок **«Personal Access Tokens» → «Create new token»**.
4. Задать имя (например `hermes-mcp`), создать.
5. **Скопировать токен сразу** — он показывается один раз.

> **Если блока «Personal Access Tokens» нет или создание падает** — у инстанса
> отсутствует Passport personal access client. Создать его один раз:
>
> ```bash
> docker exec <firefly-app-container> \
>   php artisan passport:client --personal --name="hermes-mcp" --no-interaction
> ```
>
> затем повторить создание токена в UI.

### 2. Прописать токен в `.env`

```dotenv
FIREFLY_MCP_TOKEN=<вставить-personal-access-token>
# FIREFLY_MCP_PORT оставить пустым (заполнять только для локального теста)
```

### 3. Поднять контейнер

```bash
docker compose up -d --build mcp-firefly
```

`--build` обязателен: bridge-образ собирается из `services/_mcp` с
`MCP_PKG=mcp-server-firefly-iii@3.0.0` (npm-пакет ставится на этапе сборки).

Проверить, что контейнер healthy:

```bash
docker compose ps mcp-firefly      # STATUS = healthy
```

### 4. Зарегистрировать поддомен в Dokploy UI

Traefik-labels в compose **не добавляются** (как у всех сервисов). В Dokploy UI:

- поддомен `mcp-firefly.dashboard.example.com` → контейнер `mcp-firefly`, порт `8000`.

### 5. Подключить эндпоинт в Hermes

URL: `https://mcp-firefly.dashboard.example.com/mcp` (streamable-HTTP).
Собственной авторизации нет — защита сетевая (Tailscale).

## Проверка (verify)

Локально (с заданным `FIREFLY_MCP_PORT`, напр. `8768`) или против поддомена.
streamable-HTTP отвечает SSE-кадрами `data: {...}` — ниже хелпер на curl.

```bash
U=http://127.0.0.1:8768/mcp
H=(-H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream')
post(){ curl -s -X POST "$U" "${H[@]}" -d "$1" 2>/dev/null | tr -d '\r' | sed -n 's/^data: //p'; }

# health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8768/healthz       # 200

# handshake
post '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"verify","version":"1"}}}'
curl -s -X POST "$U" "${H[@]}" -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' >/dev/null

# 66 инструментов
post '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'

# реальные данные из Firefly
post '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_about","arguments":{}}}'
post '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"list_accounts","arguments":{"type":"asset"}}}'
```

Ожидаемо: `initialize` → `serverInfo: mcp-server-firefly-iii 3.0.0`;
`tools/list` → 66 инструментов; `get_about` → версия Firefly; `list_accounts`
→ список счетов.

## Troubleshooting

| Симптом | Причина | Что делать |
| ------- | ------- | ---------- |
| `exec format error`, контейнер не стартует | взяли native amd64-образ на arm64 | использовать bridge (как в compose), не `image: ghcr.io/...` |
| Все tool-вызовы возвращают 401/403 | неверный/отозванный/просроченный токен | пересоздать Personal Access Token, обновить `FIREFLY_MCP_TOKEN`, `docker compose up -d mcp-firefly` |
| В UI нет «Personal Access Tokens» | нет Passport personal access client | `php artisan passport:client --personal` (см. шаг 1) |
| tool-вызовы возвращают connection refused | `firefly-app` не поднят / не на сети `internal` | проверить `docker compose ps firefly-app` и сеть |
| Контейнер периодически рестартует (exit 1) | известный баг supergateway 3.4.0: падает на оборванном/опоздавшем ответе (клиент отвалился посреди запроса) | `restart: unless-stopped` поднимает автоматически; при частых падениях — поднять `SUPERGATEWAY_VERSION` в `services/_mcp/Dockerfile` или перейти на `--outputTransport sse` |

## Ссылки

- [`docs/mcp/CONVENTIONS.md`](CONVENTIONS.md) — общие правила MCP-слоя
- [`docs/adr/0007-mcp-integration-topology.md`](../adr/0007-mcp-integration-topology.md) — топология, update #13
- [`services/_mcp/README.md`](../../services/_mcp/README.md) — общий bridge-образ
- [fabianonetto/mcp-server-firefly-iii](https://github.com/fabianonetto/mcp-server-firefly-iii) — пакет (66 tools)
- [Issue #13](https://github.com/prineycom/svc-personal-dashboard/issues/13)
