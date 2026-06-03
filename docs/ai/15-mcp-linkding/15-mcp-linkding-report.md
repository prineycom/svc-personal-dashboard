# Report: 15-mcp-linkding

**Plan:** docs/ai/15-mcp-linkding/15-mcp-linkding-plan.md
**Mode:** inline
**Status:** ✅ complete

## Tasks

| #   | Task                                                  | Status  | Commit    | Concerns |
| --- | ----------------------------------------------------- | ------- | --------- | -------- |
| 1   | Добавить контейнер `mcp-linkding` в docker-compose.yml | ✅ DONE | `fcb2767` | —        |
| 2   | Задокументировать Linkding-эндпоинт в CONVENTIONS.md   | ✅ DONE | `00943ea` | —        |
| 3   | Validation                                            | ✅ DONE | —         | —        |

## Post-implementation

| Step          | Status     | Commit |
| ------------- | ---------- | ------ |
| Validate      | ✅ pass    | —      |
| Documentation | ⏭️ skipped | —      |
| Format        | ⏭️ N/A     | —      |

## Validation

`docker compose config -q` ✅ (конфигурация валидна, без ошибок)
`grep -c 'linkding-mcp:v0.1.6' docker-compose.yml` ✅ → `1` (тег запиннен)
`:latest` в блоке mcp-linkding ✅ → отсутствует
Lint / type-check / test / build — N/A (инфраструктурный compose, тулчейна нет)

## Changes summary

| File                     | Action   | Description                                                          |
| ------------------------ | -------- | -------------------------------------------------------------------- |
| docker-compose.yml       | modified | Сервис `mcp-linkding` (native `:v0.1.6`, `http`, BIND_ADDR :8000, без healthcheck) |
| .env.example             | modified | Уточнён комментарий к `LINKDING_MCP_TOKEN` (источник токена → `LINKDING_API_TOKEN`) |
| docs/mcp/CONVENTIONS.md  | modified | Заметка §3: Linkding отдаёт `/mcp/v1/*`, URL для Hermes              |

## Commits

- `fcb2767` #15 feat(15-mcp-linkding): add linkding MCP native container
- `00943ea` #15 docs(15-mcp-linkding): document linkding MCP endpoint path

## Verify (ops, вне репозитория)

- `LINKDING_MCP_PORT=8100 docker compose up -d linkding mcp-linkding` → оба контейнера running.
- `curl -s -X POST http://localhost:8100/mcp/v1/tools/list` → `search_bookmarks`, `create_bookmark`, `get_tags`.
- Зарегистрировать `https://mcp-linkding.dashboard.example.com/mcp/v1` в Hermes; сохранить/найти закладку из Hermes.
- При пустом `LINKDING_MCP_TOKEN` контейнер стартует, но вызовы к Linkding API дают ошибку авторизации — токен обязателен в проде.
