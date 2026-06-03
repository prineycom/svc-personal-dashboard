# MCP-слой — конвенции Blueprint

Как каждое self-hosted направление подключается к ИИ-агенту **Hermes** через MCP.
Архитектурное решение — [ADR 0007](../adr/0007-mcp-integration-topology.md).
Глоссарий (`MCP Endpoint`, `Bridge`) — в [`CONTEXT.md`](../../CONTEXT.md).

Этот документ — образец, на который ссылаются сервисные issues #12–#17.

## 1. Транспорт: native vs bridge

Каждый MCP — отдельный контейнер в корневом `docker-compose.yml`, отдаёт
**streamable-HTTP** на порту `8000`. Два случая:

| Случай | Когда | Как |
|--------|-------|-----|
| **Native** | у MCP есть официальный образ с нативным HTTP **под нужную арку** | запускаем образ напрямую (`PORT` / `BIND_ADDR`) |
| **Bridge** | MCP только stdio, или образа нет под целевую арку | оборачиваем через [`services/_mcp/`](../../services/_mcp/) (supergateway) |

| Сервис | MCP | Транспорт |
|--------|-----|-----------|
| Vikunja | `@democratize-technology/vikunja-mcp` | bridge |
| Firefly III | `mcp-server-firefly-iii` (npm) | bridge¹ |
| Wger | `Juxsta/wger-mcp` | bridge |
| Linkding | `ghcr.io/chickenzord/linkding-mcp` | native (`BIND_ADDR`) |
| BeaverHabits | свой FastMCP | native |
| OpenTickly | свой FastMCP / форк Toggl-MCP | native |

> ¹ У Firefly III официальный образ `ghcr.io/fabianonetto/mcp-server-firefly-iii`
> публикуется только под `linux/amd64`, поэтому на Pi (arm64) не запускается
> (`exec format error`). npm-пакет `mcp-server-firefly-iii` мультиарх → оборачиваем
> его bridge'ом. Если деплой только на x86-64 — допустим и native-образ.

## 2. Размещение

- **Bridge-образ** — общий, в `services/_mcp/` (Dockerfile + README). Параметризуется build-arg `MCP_PKG`.
- **Свой FastMCP** — в `services/<svc>/mcp/` (Dockerfile + исходники).
- **Native-образ** — своей папки не требует, только блок в compose.

## 3. Сеть и роутинг

- Контейнер на сетях `internal` + `dokploy-network`.
- **Без `ports:`** — кроме escape-hatch `${<SVC>_MCP_PORT:-}:8000` для локального теста (на Dokploy пусто).
- Поддомен `mcp-<svc>.dashboard.example.com` → порт `8000` регистрируется **в Dokploy UI**.
  **Traefik-labels в compose не добавляем** — источник роутинга Dokploy UI (как у всех сервисов).
- **Путь эндпоинта.** supergateway отдаёт streamable-HTTP по умолчанию на `/mcp`
  (меняется флагом `--streamableHttpPath`), health — на `/healthz`. Полный URL,
  который регистрируется в Hermes: `https://mcp-<svc>.dashboard.example.com/mcp`.
  Native-образы могут использовать свой путь — сверяйтесь с README образа.
- Защита — Tailscale; собственной авторизации на MCP-эндпоинте нет.
- **MCP → свой сервис** ходит по `internal` (внутреннее имя хоста), не через публичный URL. Наружу через Tailscale выходит только Hermes → MCP.
- **Hermes на том же хосте (текущий случай).** Тогда поддомен не нужен — проще
  и надёжнее опубликовать фиксированный host-порт и ходить на
  `http://127.0.0.1:<port>/mcp`. Зафиксируй `<SVC>_MCP_PORT` свободным портом
  (пустое значение = случайный порт, слетает при каждом редеплое). Vikunja MCP
  закреплён на `8765` (`http://127.0.0.1:8765/mcp`). Поддомен `mcp-<svc>` нужен,
  только если Hermes когда-нибудь переедет на другую машину.

Внутренние upstream-хосты:

| Сервис | Внутренний URL |
|--------|----------------|
| Vikunja | `http://vikunja:3456` |
| Firefly III | `http://firefly-app:8080` |
| Wger | `http://wger-nginx:80` |
| Linkding | `http://linkding:9090` |
| BeaverHabits | `http://beaverhabits:8080` |
| OpenTickly | `http://opentickly:8080` |

## 4. Секреты

Токены MCP — в корневом `.env` с префиксом `<SVC>_MCP_TOKEN`; в `environment:`
мапятся на ту переменную, которую ждёт образ. Пример:

```yaml
    environment:
      FIREFLY_URL: http://firefly-app:8080
      FIREFLY_TOKEN: ${FIREFLY_MCP_TOKEN:-}   # неймспейс .env -> имя образа
```

Это сохраняет единый неймспейс в `.env`, не требуя переименования env сторонних образов.

## 5. Healthcheck и лимиты

Как у остальных сервисов: `restart: unless-stopped`, `memory: 128M`, пин тега.
Healthcheck — `wget` против health-пути (bridge: `/healthz`; native — путь образа).

## 6. Compose-сниппеты

### Native (официальный образ)

Для образа с нативным HTTP под целевую арку (Linkding, свои FastMCP):

```yaml
  mcp-<svc>:
    image: <official-image>:<pin>          # пин по тегу или @sha256
    restart: unless-stopped
    depends_on:
      <svc>:
        condition: service_started
    environment:
      <SVC>_URL: http://<svc>:<port>        # внутренний хост, не публичный URL
      <SVC>_TOKEN: ${<SVC>_MCP_TOKEN:-}
      PORT: "8000"                          # или BIND_ADDR — см. README образа
    expose:
      - "8000"
    ports:
      - ${<SVC>_MCP_PORT:-}:8000
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8000/<health-path>"]
      interval: 30s
      timeout: 5s
      retries: 5
      start_period: 20s
    deploy:
      resources:
        limits:
          memory: 128M
    networks:
      - internal
      - dokploy-network
```

### Bridge (Vikunja)

```yaml
  mcp-vikunja:
    build:
      context: ./services/_mcp
      args:
        MCP_PKG: "@democratize-technology/vikunja-mcp@0.2.0"
    restart: unless-stopped
    depends_on:
      vikunja:
        condition: service_healthy
    environment:
      VIKUNJA_URL: http://vikunja:3456/api/v1   # /api/v1 обязателен
      VIKUNJA_API_TOKEN: ${VIKUNJA_MCP_TOKEN:-}  # токен формата tk_…
    expose:
      - "8000"
    ports:
      - ${VIKUNJA_MCP_PORT:-}:8000
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 5s
      retries: 5
      start_period: 20s
    deploy:
      resources:
        limits:
          memory: 128M
    networks:
      - internal
      - dokploy-network
```

> Точные имена env-переменных зависят от пакета — сверяйтесь с его README и
> мапьте на ключи `<SVC>_MCP_*` в корневом `.env`. Для `vikunja-mcp@0.2.0`:
> `VIKUNJA_URL` (берётся как есть — суффикс `/api/v1` обязателен, иначе запросы
> уходят на фронтенд) и `VIKUNJA_API_TOKEN` (токен формата `tk_…` из UI Vikunja).

**Firefly III** использует тот же bridge — официальный образ только amd64, а
npm-пакет мультиарх. Пошаговая настройка — [`firefly-iii.md`](firefly-iii.md).
Отличие от Vikunja — `MCP_PKG` и env-переменные пакета:

```yaml
  mcp-firefly:
    build:
      context: ./services/_mcp
      args:
        MCP_PKG: "mcp-server-firefly-iii@3.0.0"
    depends_on:
      firefly-app:
        condition: service_started
    environment:
      FIREFLY_URL: http://firefly-app:8080
      FIREFLY_TOKEN: ${FIREFLY_MCP_TOKEN:-}
    # expose / ports / healthcheck (/healthz) / deploy / networks — как у mcp-vikunja
```
