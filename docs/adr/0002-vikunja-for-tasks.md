# Vikunja как трекер задач

Выбран Vikunja (Go + Vue.js) для бэклога задач и проектного управления. Детальное сравнение → vikunja-vs-plane.

## Considered Options

- **Vikunja** — Go + Vue.js, лёгкий (~13MB RAM), 3 MCP-сервера, Pi 5 совместим ✅
- **Plane.so** — Python/Django + Next.js, ~8 контейнеров, 4-8 GB RAM, overkill для одного человека
- **TickTick** — проприетарный, нет MCP, SaaS
- **YouTrack** — Java, 2GB+ RAM, командный фокус

## Why Vikunja

- Легковесный — не сожрёт ресурсы Pi 5
- 3 готовых MCP-сервера (`aimbitgmbh/vikunja-mcp`, `0xK3vin/vikunja-mcp`, `jrejaud/vikunja-mcp`)
- Импорт из Todoist/Trello
- Персональный фокус — «to-do app to organize your life»

## Consequences

- ARM64 на Pi 5 требует проверки (на Pi 4 были проблемы, на Pi 5 — работает по отчётам).