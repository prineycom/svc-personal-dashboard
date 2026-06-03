# Personal Dashboard

Единая система управления повседневной жизнью через ИИ-агента (Hermes). Гибридная архитектура: внешние сервисы только там где нет self-host аналога с同等ным качеством (Google Calendar), self-hosted для всего остального. Hermes — единая точка входа через MCP.

## Language

**Dashboard**:
Оркестрационный слой, объединяющий данные из всех направлений через MCP. Не UI-приложение, не монолитный бэкенд.
_Avoid_: приложение, платформа, система

**Direction**:
Направление жизни — самостоятельная область с собственной моделью данных и сервисом (финансы, здоровье, задачи и тд).
_Avoid_: модуль, блок, секция

**Integration**:
Способ подключения направления к Dashboard. Либо MCP-сервер внешнего сервиса, либо MCP-сервер self-hosted решения, либо встроенный инструмент Hermes.
_Avoid_: коннектор, плагин, адаптер

**Blueprint**:
Монорепо `svc-personal-dashboard` на основе template-service, деплоящееся через Dokploy. Один репозиторий содержит все сервисы; каждый сервис — в своей подпапке `services/<name>/` с `.env.example`. Корневой `docker-compose.yml` — плоский (все 12 контейнеров в одном файле, без `include`).
_Avoid_: монолит, единый compose

**Service Directory**:
Подпапка `services/<name>/` внутри Blueprint. Содержит свой docker-compose фрагмент, конфиги, `.env.example`. Изолирована от других сервисов.
_Avoid_: модуль, сервис-репо

**MCP Endpoint**:
HTTP/SSE-эндпоинт MCP-сервера направления, развёрнутый контейнером в Blueprint за Traefik-поддоменом `mcp-<service>.dashboard.example.com`. Точка, к которой подключается Hermes. Защита — Tailscale, без собственной авторизации.
_Avoid_: MCP-порт, коннектор

**Bridge**:
Контейнер с supergateway/mcpo, оборачивающий готовый stdio-only MCP-сервер в HTTP/SSE. Применяется только там, где у готового MCP нет нативного HTTP и Docker-образа (Vikunja, Wger).
_Avoid_: прокси, шлюз

## Decisions

- **Scope**: Гибрид — внешние сервисы только там где нет self-host аналога (Google Calendar). Self-host для всего остального. Hermes как единая точка входа через MCP. → [ADR 0001](docs/adr/0001-hybrid-architecture.md)
- **Ежедневник**: Не отдельный direction, а оркестрационный сценарий Hermes. Утренний/вечерний cron собирает данные из всех направлений и формирует summary.
- **Бэклог задач**: Vikunja. Анализ в vikunja-vs-plane. Легковесный (Go+Vue, ~13MB RAM), 3 MCP-сервера, Pi 5 совместим. → [ADR 0002](docs/adr/0002-vikunja-for-tasks.md)
- **Фокус-цели**: Self-hosted решение (своя разработка, позже). Временно — через MCP Dashboard.
- **Финансы**: Firefly III (self-hosted). Без банк-синхронизации, ручной ввод + CSV. MCP: `fabianonetto/mcp-server-firefly-iii` (66 инструментов). → [ADR 0003](docs/adr/0003-firefly-iii-finances.md)
- **Здоровье (gym + питание)**: Wger (self-hosted). MCP: `Juxsta/wger-mcp` (8 инструментов). Базовые замеры — позже.
- **Трекер привычек**: BeaverHabits (self-hosted). Rust + SQLite, ультра-лёгкий. MCP-обёртку написать.
- **Тайм-трекер**: OpenTickly (self-hosted). Toggl API-compatible, AI-CLI, OpenAPI spec. MCP-обёртка поверх Toggl API.
- **Почта**: Gmail через встроенный Hermes-скилл Google Workspace. OAuth2 авторизация. Не входит в Blueprint — используется встроенная интеграция Hermes. **Setup pending** (Google Cloud проект + OAuth креды).
- **Календарь**: Google Calendar через тот же скилл Google Workspace (SaaS — исключение). Полный CRUD: list, create, delete events. Не входит в Blueprint. → [ADR 0004](docs/adr/0004-google-calendar-saas.md)
- **Контакты**: Не priority. Резерв: OxiCloud или Radicale.
- **Закладки/Медиа**: Linkding (self-hosted). Ультра-лёгкий (1 контейнер, ~60 МБ RAM, SQLite), 2 MCP-сервера, ARM64 alpine, авто-архивация через Internet Archive. AI tagging/summaries — через Hermes при сохранлении. → [ADR 0005](docs/adr/0005-linkding-for-bookmarks.md)
- **MCP Dashboard**: Отключён. Создан преждевременно. Вернуть после редизайна.
- **Топология интеграции (этап 2)**: Каждое self-hosted направление — remote MCP по HTTP/SSE, контейнер в Blueprint, за Traefik-поддоменом `mcp-<service>.dashboard.example.com`, защита Tailscale. Готовые stdio-MCP оборачиваются supergateway (Bridge), но только без нативного HTTP/образа: Firefly III и Linkding имеют официальный образ с HTTP → напрямую. Свои MCP — Python + FastMCP. Креды сервисов — в корневом `.env`. → [ADR 0007](docs/adr/0007-mcp-integration-topology.md)
  - **Vikunja**: `democratize-technology/vikunja-mcp` (TS, полное покрытие) + supergateway.
  - **Firefly III**: `fabianonetto/mcp-server-firefly-iii` (66 tools), нативный HTTP, официальный образ.
  - **Wger**: `Juxsta/wger-mcp` (12 tools) + supergateway. Риск: проверить настраиваемость URL self-hosted инстанса.
  - **Linkding**: `chickenzord/linkding-mcp` (Go), нативный HTTP. Официальный образ хардкодит `GOARCH=amd64` (битый arm64) → собираем из исходников в `services/linkding/mcp/`.
  - **BeaverHabits**: свой FastMCP поверх REST API (`/api/v1/...`).
  - **OpenTickly**: свой FastMCP поверх Toggl API v9 — или форк Toggl-MCP с override base URL.
- **Деплой**: Монорепо Blueprint `prineycom/svc-personal-dashboard` (private) на основе template-service. Плоский `docker-compose.yml` — все 12 контейнеров в одном файле. Каждый сервис в `services/<name>/` с `.env.example` для читаемости. Один репозиторий, один Dokploy deploy. → [ADR 0006](docs/adr/0006-monorepo-blueprint.md)
- **Прежний `personal-dashboard`**: Удалён/переделан. Не референсировать, не переносить код.
- **Shared PostgreSQL**: Один инстанс PostgreSQL 17 (описан в корневом compose) с отдельными базами для Vikunja, Firefly III, Wger, OpenTickly. BeaverHabits и Linkding используют встроенный SQLite.
- **Shared Redis**: Один инстанс Redis (описан в корневом compose) для Wger (celery) и других сервисов.
- **Доступ**: Все сервисы за Tailscale. Авторизация не критична — каждый сервис имеет свой логин, но реальная защита сетевая (Tailscale WireGuard). SSO не нужен.

## Service Images

| Сервис | Образ | Контейнеров | База | RAM (idle) | ARM64 |
|--------|-------|-------------|------|------------|-------|
| Infra | `postgres:17-alpine` | 1 | Shared | ~50 MB | ✅ |
| Infra | `redis:7-alpine` | 1 | Shared | ~20 MB | ✅ |
| Vikunja | `vikunja/vikunja:2.3.0` | 1 | Shared PG | ~30-50 MB | ✅ |
| Firefly III | `fireflyiii/core:version-6.6.3` + `alpine` cron | 2 | Shared PG | ~100-170 MB | ✅ |
| Wger | `wger/server:2.5` + `nginx:stable` + celery_worker + celery_beat | 4 | Shared PG + Redis | ~190 MB | ✅ |
| Linkding | `sissbruecker/linkding:1.45.0-alpine` | 1 | SQLite | ~50 MB | ✅ |
| BeaverHabits | `daya0576/beaverhabits:0.9.1` | 1 | SQLite (DATABASE mode) | ~10-20 MB | ✅ |
| OpenTickly | `correctroad/opentoggl:0.2.16` | 1 | Shared PG + Redis | ~30-50 MB | ✅ |

**Итого: 12 контейнеров, ~900 MB idle / ~1.3 GB peak RAM.**

## Architecture Split

**В Blueprint (Docker Compose):**
1. PostgreSQL 17 + Redis 7 — в корневом `docker-compose.yml`
2. `services/vikunja/` — задачи (1 контейнер)
3. `services/firefly-iii/` — финансы (2 контейнера: app + cron)
4. `services/wger/` — здоровье (4 контейнера: web, nginx, celery_worker, celery_beat)
5. `services/linkding/` — закладки (1 контейнер)
6. `services/beaverhabits/` — привычки (1 контейнер)
7. `services/opentickly/` — тайм-трекинг (1 контейнер)

**Через Hermes-скиллы (вне compose):**
- Почта (Gmail) — Google Workspace скилл
- Календарь — Google Workspace скилл

## Routing

Роутинг через Traefik (управляется Dokploy UI, не в compose):

| Сервис | Поддомен |
|--------|----------|
| Vikunja | `tasks.dashboard.example.com` |
| Firefly III | `finance.dashboard.example.com` |
| Wger | `fitness.dashboard.example.com` |
| Linkding | `bookmarks.dashboard.example.com` |
| BeaverHabits | `habits.dashboard.example.com` |
| OpenTickly | `time.dashboard.example.com`

## Example Dialogue

> **Паша**: "Сколько я потратил на еду в мае?"
> **При**: *Вызывает Firefly III MCP → `get_transactions` с фильтром по категории и дате* → "В мае ты потратил на еду 23,450 ₽. Это на 12% больше чем в апреле."
>
> **Паша**: "Запланируй тренировку на спину завтра в 10 утра."
> **При**: *Вызывает Wger MCP → `create_workout`* → *Вызывает Google Calendar MCP → `create_event`* → "Готово: тренировка на спину завтра 10:00. Добавил в календарь."
>
> **Паша**: "Сохрани эту статью на потом."
> **При**: *Вызывает Linkding MCP → `create_bookmark` + AI summary через LLM* → "Сохранила. Тема: архитектура микросервисов. Метки: dev, architecture."
>
> **Паша**: "Утренний обзор."
> **При**: *Cron собирает: Vikunja задачи на сегодня, Firefly III баланс, BeaverHabits утренние привычки, Wger запланированную тренировку, OpenTickly вчерашнее время, Linkding непрочитанные закладки, Google Calendar события* → формирует summary.
>
> **Паша**: "Добавь новый сервис в дашборд."
> **При**: *Создаёт новую Service Directory `services/<name>/` в Blueprint, добавляет include в корневой compose, пушит* → "Готово. После деплоя новый сервис поднимется автоматически."