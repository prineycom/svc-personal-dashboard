# Топология интеграции сервисов с Hermes через MCP

Этап 2: каждое self-hosted направление подключается к Hermes как **remote MCP-сервер по HTTP/SSE**, развёрнутый контейнером в Blueprint на Pi, за Traefik-поддоменом, защищённый сетью Tailscale. Hermes транспорт-агностичен (любой MCP + CLI), поэтому выбор транспорта и хостинга — на стороне Blueprint.

## Considered Options

**Где крутятся MCP-серверы:**
- **A) В Blueprint на Pi (remote HTTP/SSE)** ✅ — каждый MCP контейнер рядом с сервисом, Hermes ходит по сети. Централизованно, в одном репо, не зависит от машины Hermes.
- **B) Рядом с Hermes (stdio/local)** — привязано к машине Hermes, до сервисов ходит по API через Tailscale.
- **C) Гибрид по транспорту**

**Как поступать со сторонними stdio-MCP:**
- **A) Обёртка мостом (supergateway/mcpo)** ✅ — берём готовый stdio-MCP, в контейнере оборачиваем в streamable-HTTP/SSE. Минимум своего кода.
- **B) Только нативный HTTP или свой MCP**

**Как Hermes достучится до MCP:**
- **A) Traefik-поддомены** ✅ — Traefik уже работает (Dokploy), доп. контейнеров и RAM ≈ 0, TLS из коробки, единообразно с сервисами.
- **B) Один шлюз/порт** — лишний контейнер или менее прозрачный path-routing.
- **C) Host-порты + Tailscale IP** — Traefik всё равно запущен, реальной экономии нет; теряется TLS, ручной учёт портов.

**Язык собственных MCP:**
- **A) Python + FastMCP** ✅ — нативный streamable-HTTP, без supergateway, лёгкий образ, де-факто стандарт.
- **B) TypeScript SDK**

## Decision

1. **Транспорт**: remote HTTP/SSE. MCP-серверы — контейнеры в корневом `docker-compose.yml`, как и сервисы.
2. **Готовые stdio-MCP оборачиваем supergateway** — те, у кого нет нативного HTTP/Docker **под целевую арку**. Linkding имеет официальный multi-arch образ с нативным HTTP — запускаем напрямую. Firefly III: официальный образ только amd64 (см. update ниже) — оборачиваем npm-пакет мостом.
3. **Доступ через Traefik-поддомены** (`mcp-<service>.dashboard.example.com`), управление в Dokploy UI, как у сервисов. Защита — Tailscale (отдельная авторизация на MCP-эндпоинте не вводится, согласно [ADR 0001] решению «защита сетевая»).
4. **Собственные MCP — Python + FastMCP** (нативный HTTP), для BeaverHabits и OpenTickly (позже focus-goals).
5. **Креды сервисов** (API-токены) живут в корневом `.env`, пробрасываются в MCP-контейнеры через `environment`-блок — как уже сделано для сервисов.

## Per-service mapping

| Сервис | MCP-решение | Транспорт | Стратегия контейнера |
|--------|-------------|-----------|----------------------|
| Vikunja | `democratize-technology/vikunja-mcp` (TS, полное покрытие) | stdio | **supergateway-обёртка**, свой образ |
| Firefly III | `mcp-server-firefly-iii` (66 tools, npm) | stdio → HTTP | **supergateway-обёртка** (`services/_mcp`); официальный образ только amd64 — см. update |
| Wger | `Juxsta/wger-mcp` (12 tools, TS) | stdio | **supergateway-обёртка**; риск: проверить настраиваемость URL self-hosted инстанса |
| Linkding | `chickenzord/linkding-mcp` (Go) | **нативный HTTP** (`BIND_ADDR`) | официальный образ `ghcr.io/...`, **без моста** |
| BeaverHabits | свой (REST API `/api/v1/...` есть) | нативный HTTP (FastMCP) | свой образ Python |
| OpenTickly | свой FastMCP поверх Toggl API v9 — **или** форк готового Toggl-MCP с override базового URL | нативный HTTP | свой образ Python |

## Consequences

- В compose добавляется ~6 MCP-контейнеров. RAM-бюджет вырастет (оценить при реализации; supergateway-обёртки на Node — самые тяжёлые).
- Для Vikunja и Wger нужен свой Dockerfile (готовых образов нет) поверх npx + supergateway.
- Wger MCP — риск hardcoded публичного API URL; если URL не настраивается, форкнуть или написать свой.
- OpenTickly: Toggl-совместимость даёт шанс переиспользовать готовый Toggl-MCP, если он позволяет переопределить base URL; иначе свой FastMCP.
- Каждый MCP-эндпоинт открыт без собственной авторизации — допустимо только за Tailscale. Если Hermes будет работать вне Tailscale, потребуется пересмотр.

## Update (2026-06-02, #13)

Образ `ghcr.io/fabianonetto/mcp-server-firefly-iii` публикуется только под
`linux/amd64` (single-arch manifest, без arm64). На Pi 5 (arm64) — `exec format
error`. Поэтому Firefly III переведён из native в **bridge**: npm-пакет
`mcp-server-firefly-iii` мультиарх, оборачивается общим `services/_mcp`
(supergateway), транспорт — streamable-HTTP `/mcp`. Если деплой только на
x86-64, native-образ остаётся допустимым вариантом. Критерий native/bridge
уточнён: нативный образ должен иметь сборку под целевую арку.

[ADR 0001]: 0001-hybrid-architecture.md
