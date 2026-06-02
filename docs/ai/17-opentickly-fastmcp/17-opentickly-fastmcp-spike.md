# Спайк: форк готового Toggl-MCP vs свой FastMCP

**Задача:** [17-opentickly-fastmcp](17-opentickly-fastmcp-task.md) · Task 1 (gate)
**Дата:** 2026-06-02
**Решение:** ✅ Пишем **свой** Python + FastMCP.

## Вопрос

Можно ли форкнуть готовый Toggl-MCP с override base URL на OpenTickly
(`http://opentickly:8080`), чтобы не писать свой? И отдаёт ли OpenTickly
Reports API v3 для тула `get_report`?

## Кандидаты

### `verygoodplugins/mcp-toggl` — ❌ нет override base URL

- **Стек:** Node.js / TypeScript (Node `^20.19` / `>=22.12`).
- **Base URL захардкожен в исходниках** (`src/toggl-api.ts`):
  ```ts
  private baseUrl = 'https://api.track.toggl.com/api/v9';
  private timelineBaseUrl = 'https://track.toggl.com/api/v9';
  ```
- Env-переменных для смены хоста нет: читает `TOGGL_API_KEY` / `TOGGL_API_TOKEN` /
  `TOGGL_TOKEN`, `TOGGL_DEFAULT_WORKSPACE_ID`, кэш-настройки.
- 16 тулов (Reports, Timer Control, Lookups, Cache) — избыточно для наших 4.
- **Вывод:** форк = патч двух захардкоженных констант + поддержка TS-форка и его
  релиз-цикла. Дороже своего.

### `KyteProject/togglgo-mcp` — ❌ нет override, нет отчётов

- **Стек:** Go 1.21+.
- Читает только `TOGGL_API_TOKEN`; override base URL в README/конфиге не описан.
- Тулы: `start_time_entry`, `stop_time_entry`, `get_current_time_entry`,
  `get_time_entries`, `get_time_entries_for_day`, `create_project`, `get_projects`.
  **Нет get_report** (Reports v3 не покрыт).
- **Вывод:** не закрывает требование `get_report`, override тоже не из коробки.

## Reports API v3 в OpenTickly

OpenTickly (`correctroad/opentoggl`) в `CONTEXT.md` и epic #9 заявлен как
Toggl API-совместимый: **Track API v9 + Reports API v3**, с OpenAPI spec.
Статически подтвердить набор Reports-эндпоинтов по публичному репозиторию не
удалось (репозиторий исходников недоступен/закрыт). `get_report` реализуем под
путь Reports v3 (`/reports/api/v3/workspace/{wid}/search/time_entries`);
рантайм-подтверждение — на шаге Verify (ручной вызов из Hermes против живого
контейнера `opentickly`).

## Решение и обоснование

**Свой Python + FastMCP** в `services/opentickly/mcp/`:

- Полный контроль base URL → `http://opentickly:8080` (сеть `internal`), без
  патча чужих констант.
- Ровно 4 нужных тула, native streamable-HTTP, без лишних 16 тулов и кэш-слоёв.
- Нет зависимости от чужого релиз-цикла и форк-долга.
- Соответствует конвенции `docs/mcp/CONVENTIONS.md` («свой FastMCP — native»).

Implementation-задачи плана (Task 2–8) идут без изменений.
