# Report: 10-mcp-conventions

**Plan:** docs/ai/10-mcp-conventions/10-mcp-conventions-plan.md
**Mode:** inline
**Status:** ✅ complete

## Tasks

| # | Task | Status | Commit | Concerns |
|---|------|--------|--------|----------|
| 1 | Bridge-образ + документ конвенций | ✅ DONE | `d056c3d` | — |
| 2 | Вынести конвенции в .env.example и README | ✅ DONE | `8f47a3a` | — |
| 3 | Validation | ✅ DONE | — | — |

## Post-implementation

| Step | Status | Commit |
|------|--------|--------|
| Validate | ✅ pass | — |
| Documentation | ⏭️ skipped (UPDATE_DOCS=false) | — |
| Format | ⏭️ skipped (нет настроенного форматтера) | — |

## Validation

`docker compose config -q` ✅ (exit 0)
`docker build --build-arg MCP_PKG=@democratize-technology/vikunja-mcp@0.2.0 services/_mcp` ✅ (образ собирается, без warnings)
`test -f services/_mcp/Dockerfile && test -f docs/mcp/CONVENTIONS.md` ✅
lint / type-check / unit-tests — N/A (compose-репо, своего тест-раннера нет)

## Changes summary

| File | Action | Description |
|------|--------|-------------|
| `services/_mcp/Dockerfile` | created | Переиспользуемый supergateway-мост stdio→HTTP, параметр `MCP_PKG`, JSON-exec CMD |
| `services/_mcp/README.md` | created | Как добавить bridged-MCP, таблица потребителей |
| `docs/mcp/CONVENTIONS.md` | created | Центральный документ: транспорт, размещение, сеть/роутинг, секреты, healthcheck, compose-сниппеты |
| `.env.example` | modified | Секция MCP-токенов `<SVC>_MCP_TOKEN` + локальные `*_MCP_PORT` |
| `README.md` | modified | Подраздел «MCP layer (stage 2)» с таблицей и ссылками |

## Commits

- `1de94c2` #10 docs(10-mcp-conventions): add implementation plan
- `d056c3d` #10 feat(10-mcp-conventions): add reusable MCP bridge image and conventions doc
- `8f47a3a` #10 docs(10-mcp-conventions): surface MCP layer in .env.example and README

## Notes

- Решение DD-3 расходится с формулировкой issue #10 («+ набор labels»): в этом
  репо роутинг управляется Dokploy UI, Traefik-labels в compose не кладут
  (revert-коммит `00f26e5`). Конвенции это учитывают.
- Bridge-образ реально собран и проверен на пакете Vikunja MCP — шаблон рабочий.
- MCP-сервисы в живой `docker-compose.yml` пока не добавлены — это сервисные
  issues #12–#17, опирающиеся на этот образец.
