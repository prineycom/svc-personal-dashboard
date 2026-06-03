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
| **Native** | у MCP есть официальный образ с нативным HTTP | запускаем образ напрямую (`PORT` / `BIND_ADDR`) |
| **Bridge** | MCP только stdio, образа нет | оборачиваем через [`services/_mcp/`](../../services/_mcp/) (supergateway) |

| Сервис | MCP | Транспорт |
|--------|-----|-----------|
| Vikunja | `@democratize-technology/vikunja-mcp` | bridge |
| Firefly III | `ghcr.io/fabianonetto/mcp-server-firefly-iii` | native (`PORT`) |
| Wger | `Juxsta/wger-mcp` | bridge |
| Linkding | `chickenzord/linkding-mcp` | native (`BIND_ADDR`), build from source¹ |
| BeaverHabits | свой FastMCP | native |
| OpenTickly | свой FastMCP / форк Toggl-MCP | native |

> ¹ Официальный образ `ghcr.io/chickenzord/linkding-mcp` хардкодит `GOARCH=amd64`,
> поэтому его «arm64»-вариант содержит x86-64 бинарь и падает на Pi с
> `exec format error`. Собираем из исходников под нативную архитектуру —
> [`services/linkding/mcp/Dockerfile`](../../services/linkding/mcp/Dockerfile).

## 2. Размещение

- **Bridge-образ** — общий, в `services/_mcp/` (Dockerfile + README). Параметризуется build-arg `MCP_PKG`.
- **Свой FastMCP** — в `services/<svc>/mcp/` (Dockerfile + исходники).
- **Native-образ** — своей папки не требует, только блок в compose. Исключение —
  Linkding: официальный образ битый под arm64, поэтому собираем из исходников в
  `services/linkding/mcp/` (Dockerfile клонирует upstream на пиннутом теге).

## 3. Сеть и роутинг

- Контейнер на сетях `internal` + `dokploy-network`.
- **Без `ports:`** — кроме escape-hatch `${<SVC>_MCP_PORT:-}:8000` для локального теста (на Dokploy пусто).
- Поддомен `mcp-<svc>.dashboard.example.com` → порт `8000` регистрируется **в Dokploy UI**.
  **Traefik-labels в compose не добавляем** — источник роутинга Dokploy UI (как у всех сервисов).
- **Путь эндпоинта.** supergateway отдаёт streamable-HTTP по умолчанию на `/mcp`
  (меняется флагом `--streamableHttpPath`), health — на `/healthz`. Полный URL,
  который регистрируется в Hermes: `https://mcp-<svc>.dashboard.example.com/mcp`.
  Native-образы могут использовать свой путь — сверяйтесь с README образа.
  - **Linkding** (`services/linkding/mcp/`, собран из исходников) — стандартный
    MCP streamable-HTTP на go-sdk; хендлер отвечает на любом пути (`/`, `/mcp`).
    URL для Hermes: `https://mcp-linkding.dashboard.example.com/mcp`.
- Защита — Tailscale; собственной авторизации на MCP-эндпоинте нет.
- **MCP → свой сервис** ходит по `internal` (внутреннее имя хоста), не через публичный URL. Наружу через Tailscale выходит только Hermes → MCP.

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

### Native (Firefly III)

```yaml
  mcp-firefly:
    image: ghcr.io/fabianonetto/mcp-server-firefly-iii:<pin>
    restart: unless-stopped
    depends_on:
      firefly-app:
        condition: service_started
    environment:
      FIREFLY_URL: http://firefly-app:8080
      FIREFLY_TOKEN: ${FIREFLY_MCP_TOKEN:-}
      PORT: "8000"
    expose:
      - "8000"
    ports:
      - ${FIREFLY_MCP_PORT:-}:8000
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
      VIKUNJA_URL: http://vikunja:3456
      VIKUNJA_API_TOKEN: ${VIKUNJA_MCP_TOKEN:-}
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
> мапьте на ключи `<SVC>_MCP_*` в корневом `.env`.
