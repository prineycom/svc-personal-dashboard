# svc-personal-dashboard

Personal Dashboard — deployment blueprint for Dokploy. One monorepo, one `docker compose up`, seven self-hosted services behind Tailscale. Shared PostgreSQL 17 + Redis in the flat root compose. Hermes AI agent as orchestration layer via MCP.

## Architecture

```
svc-personal-dashboard/
├── CONTEXT.md              ← project glossary & decisions
├── docs/adr/               ← architecture decision records
├── docker-compose.yml      ← flat compose — all 12 containers in one file
├── .env.example            ← shared env vars
├── services/
│   ├── vikunja/            ← task backlog (.env.example)
│   ├── firefly-iii/        ← finance tracker (.env.example)
│   ├── wger/               ← gym + nutrition (.env.example)
│   ├── linkding/           ← bookmarks (.env.example)
│   ├── beaverhabits/       ← habit tracker (.env.example)
│   └── opentickly/         ← time tracker (.env.example)
└── README.md
```

## Services (self-hosted, in compose)

| Service | What | DB | RAM (idle) | MCP |
|---------|------|----|------------|-----|
| [Vikunja](https://vikunja.io) | Tasks | Shared PG | ~30-50 MB | 3 servers |
| [Firefly III](https://firefly-iii.org) | Finances | Shared PG | ~100-170 MB | 3 servers |
| [Wger](https://wger.de) | Gym + Nutrition | Shared PG | ~190 MB | 1 server |
| [Linkding](https://github.com/sissbruecker/linkding) | Bookmarks | SQLite | ~50-80 MB | 2 servers |
| [BeaverHabits](https://github.com/daya0576/beaverhabits) | Habits | SQLite | ~10-20 MB | wrapper TBD |
| [OpenTickly](https://github.com/CorrectRoadH/OpenTickly) | Time tracking | Shared PG | ~30-50 MB | wrapper TBD |

## Outside compose (Hermes skills)

- **Email** — Gmail via `google-workspace` skill (OAuth2)
- **Calendar** — Google Calendar via `google-workspace` skill

## Conventions

- **HTTP via Traefik only** — no `ports:` on web services.
- **Raw TCP exception** — PostgreSQL can be published via `DB_PUBLIC_PORT` (requires strong password + fail2ban).
- **Pin image tags** — never `:latest`.
- **Nothing machine-specific in git** — domains, secrets, limits in Dokploy env.
- **Memory limits** on every service — Pi 5 has no swap.

## Deploy

1. Push to `main` → Dokploy auto-deploys (if webhook is set).
2. Set env vars in Dokploy UI (see `.env.example` files in each service dir).
3. All services join `dokploy-network`; private deps (PG, Redis) on `internal`.

## Resource budget

- **Peak**: ~1.3 GB RAM (on 8 GB Pi 5)
- **Idle**: ~900 MB
- **Free**: ~6.7 GB
