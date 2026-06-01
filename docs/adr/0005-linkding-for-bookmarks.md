# Linkding для закладок/медиа

Выбран Linkding (Django, SQLite, 1 контейнер) для закладок и read-later. Заменил Karakeep и Linkwarden.

## Considered Options

- **Karakeep** (ex-Hoarder) — AI tagging + summaries, Meilisearch FTS, 3 контейнера, ~500 МБ RAM. ❌ Chrome headless нет ARM64 образа, RAM-голодный, MCP нет, 25.6k ★
- **Linkwarden** — full-page archive, highlights, MCP есть. ❌ нет AI summaries, 2-3 контейнера, ~250 МБ
- **Linkding** ✅ — 1 контейнер, ~60 МБ RAM, 2 MCP-сервера (`chickenzord/linkding-mcp`, `jensneuhaus/linkding-mcp`), ARM64 alpine, авто-архивация через Internet Archive/HTML
- **Readeck** — Go single binary, highlights, EPUB export, MCP есть. ❌ молодой (~1k ★), нет full-text search, нет page archive
- **Shiori** — Go CLI, 1 контейнер. ❌ нет MCP, нет AI, медленная разработка

## Why Linkding

1. **Ультра-лёгкий** — 1 контейнер с SQLite, ~60 МБ RAM. Экономия ~440 МБ vs Karakeep
2. **MCP уже есть** — не нужно писать обёртку
3. **ARM64 без проблем** — alpine-образ
4. **Авто-архивация** — Internet Archive Wayback Machine или локальный HTML
5. **Браузерные расширения** + PWA для телефона
6. **REST API** — документирован

## Trade-off

- Нет AI tagging/summaries из коробки — Hermes делает summary через LLM при сохранении
- Нет full-text search по содержимому страниц — приемлемо для закладок (поиск по тегам и заголовкам)
- Нет highlights/annotations — если станет нужно, migrare на Readeck или Linkwarden

## Supersedes

Заменяет 0005-karakeep-over-linkwarden|ADR-0005 (Karakeep over Linkwarden).