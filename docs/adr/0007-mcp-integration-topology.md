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
2. **Готовые stdio-MCP оборачиваем supergateway** — но только те, у кого нет нативного HTTP/Docker. Firefly III и Linkding имеют нативный HTTP — мост не нужен. Firefly III запускаем из официального образа; у Linkding официальный образ битый под arm64 (хардкод `GOARCH=amd64`), поэтому собираем из исходников в `services/linkding/mcp/`.
3. **Доступ через Traefik-поддомены** (`mcp-<service>.dashboard.example.com`), управление в Dokploy UI, как у сервисов. Защита — Tailscale (отдельная авторизация на MCP-эндпоинте не вводится, согласно [ADR 0001] решению «защита сетевая»).
4. **Собственные MCP — Python + FastMCP** (нативный HTTP), для BeaverHabits и OpenTickly (позже focus-goals).
5. **Креды сервисов** (API-токены) живут в корневом `.env`, пробрасываются в MCP-контейнеры через `environment`-блок — как уже сделано для сервисов.

## Per-service mapping

| Сервис | MCP-решение | Транспорт | Стратегия контейнера |
|--------|-------------|-----------|----------------------|
| Vikunja | `democratize-technology/vikunja-mcp` (TS, полное покрытие) | stdio | **supergateway-обёртка**, свой образ |
| Firefly III | `fabianonetto/mcp-server-firefly-iii` (66 tools) | **нативный HTTP/SSE** (`PORT`) | официальный образ `ghcr.io/...`, **без моста** |
| Wger | `Juxsta/wger-mcp` (12 tools, TS) | stdio | **supergateway-обёртка**; риск: проверить настраиваемость URL self-hosted инстанса |
| Linkding | `chickenzord/linkding-mcp` (Go) | **нативный HTTP** (`BIND_ADDR`) | сборка из исходников (`services/linkding/mcp/`)¹, **без моста** |
| BeaverHabits | свой (REST API `/api/v1/...` есть) | нативный HTTP (FastMCP) | свой образ Python |
| OpenTickly | свой FastMCP поверх Toggl API v9 — **или** форк готового Toggl-MCP с override базового URL | нативный HTTP | свой образ Python |

> ¹ Официальный образ `ghcr.io/chickenzord/linkding-mcp` хардкодит `GOARCH=amd64`
> в своём Dockerfile, поэтому «arm64»-вариант содержит x86-64 бинарь и падает на
> Pi с `exec format error` (проверено при реализации #15). Собираем из исходников
> под нативную архитектуру — `services/linkding/mcp/Dockerfile`.

## Consequences

- В compose добавляется ~6 MCP-контейнеров. RAM-бюджет вырастет (оценить при реализации; supergateway-обёртки на Node — самые тяжёлые).
- Для Vikunja и Wger нужен свой Dockerfile (готовых образов нет) поверх npx + supergateway.
- Wger MCP — риск hardcoded публичного API URL; если URL не настраивается, форкнуть или написать свой.
- OpenTickly: Toggl-совместимость даёт шанс переиспользовать готовый Toggl-MCP, если он позволяет переопределить base URL; иначе свой FastMCP.
- Каждый MCP-эндпоинт открыт без собственной авторизации — допустимо только за Tailscale. Если Hermes будет работать вне Tailscale, потребуется пересмотр.

[ADR 0001]: 0001-hybrid-architecture.md
