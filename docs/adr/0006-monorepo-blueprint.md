# ADR 0006: Монорепо Blueprint вместо отдельных svc-* репозиториев

## Контекст

Семь self-hosted сервисов (Vikunja, Firefly III, Wger, Linkding, Cron Habits, OpenTickly, инфра) нуждаются в деплое через Dokploy. Есть два подхода к организации репозиториев:

**A)** Отдельные репо `svc-<name>` — каждый штампуется из `template-service`
**B)** Один монорепо `svc-personal-dashboard` с папками `services/<name>/`

## Решение

Вариант **B** — монорепо Blueprint.

Структура:

```
svc-personal-dashboard/
├── CONTEXT.md
├── docs/adr/
├── docker-compose.yml         ← корневой compose, ссылается на services/
├── .env.example               ← общие переменные
├── services/
│   ├── vikunja/
│   │   ├── docker-compose.yml ← сервисный compose-фрагмент
│   │   ├── .env.example
│   │   └── config/
│   ├── firefly-iii/
│   │   ├── docker-compose.yml
│   │   ├── .env.example
│   │   └── config/
│   ├── wger/
│   ├── linkding/
│   ├── beaverhabits/
│   ├── opentickly/
│   └── infra/                 ← shared PostgreSQL + Redis
└── README.md
```

## Причины

1. **Простота управления** — один репозиторий, один Dokploy deploy, один git push
2. **Isolation** — каждый сервис в своей папке, свои конфиги, свой `.env.example`
3. **Shared infra** — PostgreSQL и Redis вынесены в `services/infra/`, доступны всем
4. **Расширяемость** — добавить сервис = добавить папку
5. **Согласованность** — CONTEXT.md и ADRs живут рядом с деплой-кодом

## Сборка: Docker Compose `include`

Корневой `docker-compose.yml` использует `include` (Compose v2.24+):

```yaml
include:
  - services/infra/docker-compose.yml
  - services/vikunja/docker-compose.yml
  - services/firefly-iii/docker-compose.yml
  - services/wger/docker-compose.yml
  - services/linkding/docker-compose.yml
  - services/beaverhabits/docker-compose.yml
  - services/opentickly/docker-compose.yml
```

Каждый `services/<name>/docker-compose.yml` — полноценный compose-файл, запускемый и изолированно (`docker compose -f services/vikunja/docker-compose.yml up`), и через корневой `include`.

Комментарий при `include`: общие сети (`dokploy-network`, `internal`) и shared-томы (PostgreSQL, Redis) объявляются в `services/infra/docker-compose.yml`; остальные compose-файлы ссылаются на них как на `external`.

## Последствия

- Все сервисы деплоятся одновременно при `docker compose up` из корня
- Каждый сервис можно запустить изолированно из своей папки (если shared-инфра уже поднята)
- Dokploy деплоит из корня → при push пересоздаётся всё
- Нужно аккуратно управлять shared инфраструктурой (PostgreSQL, Redis) — рестарт одного сервиса не должен ронить shared DB
- `include` требует Compose v2.24+ — нужно проверить совместимость Dokploy