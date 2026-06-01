# Google Calendar как SaaS-исключение при приоритете self-host

В приоритете self-host, но календарь — исключение.

## Considered Options

- **Proton Calendar** — нет CalDAV, нет API, read-only через ICS. E2E шифрование несовместимо с CalDAV. ❌
- **iCloud Calendar** — нет REST API, только CalDAV. Community MCP есть, но ограничения. ❌
- **OxiCloud** — молодой, нет recurring events, нет UI календаря. ❌ (пока)
- **Radicale** — нет UI, нет REST API. Ультра-минимален. ❌
- **Google Calendar** ✅ — официальный MCP-сервер от Google (12+ инструментов, полный CRUD), CalDAV через OAuth, community MCP `nspady/google-calendar-mcp`

## Consequences

- Данные календаря у Google — принятый trade-off за интеграционный потенциал.
- Когда OxiCloud дозреет (recurring events + UI) — миграция возможна через CalDAV.