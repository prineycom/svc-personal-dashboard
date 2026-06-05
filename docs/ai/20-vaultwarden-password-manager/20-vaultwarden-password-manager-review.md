# Code Review: 20-vaultwarden-password-manager

## Summary

### Context and goal

Add a self-hosted Vaultwarden (Bitwarden-compatible) password manager to the flat docker-compose Blueprint as a single arm64 container with embedded SQLite, per issue #20. Closes the "passwords" direction without adding a DB dependency.

### Key code areas for review

1. **`docker-compose.yml` `vaultwarden:` block** — image pin, port-80 mapping, named volume, 192M limit, networks. Models the Linkding single-SQLite pattern.
2. **`.env.example` + `services/vaultwarden/.env.example`** — the env contract (`DOMAIN`, `SIGNUPS_ALLOWED`, `ADMIN_TOKEN`, `PORT`) must stay in sync with the compose `${VAR}` references.
3. **`CONTEXT.md`** — Service Images row, container/RAM totals (→13 / ~950 MB), Architecture Split, Routing subdomain.

### Complex decisions

1. **Port 80 target** (`docker-compose.yml`) — Vaultwarden's Rocket server listens on container port 80 (unlike Linkding's 9090); host-published only via `${VAULTWARDEN_PORT:-}` for local test, empty in prod (Traefik).
2. **No healthcheck** — matches Linkding; avoids the minimal-image probe trap that bit Vikunja.
3. **192M memory** — raised from the planned 128M after review: server-side Argon2id `ADMIN_TOKEN` verification spikes ~64 MiB transiently on `/admin` login.

### Questions for the reviewer

1. The real production `DOMAIN` must be `https://` (WebAuthn/passkeys) and set in Dokploy — confirm Traefik terminates TLS for `passwords.dashboard.example.com`.
2. `SIGNUPS_ALLOWED=true` is intentional (Tailscale-gated, per task decision) — confirm you want signups left open long-term rather than closing them after first registration.

### Risks and impact

- **Open signups**: anyone with Tailscale network access can register. Accepted per the task's threat model.
- **Admin token**: must be an Argon2 PHC hash generated with `docker run --rm -it vaultwarden/server /vaultwarden hash`; an empty value disables `/admin` (verified).
- **Memory on no-swap Pi 5**: 192M gives headroom for the Argon2 login spike; concurrent admin logins remain the only realistic pressure point.

### Tests and manual checks

**Auto-tests:** none — compose-only repo. `docker compose config -q` is the gate (passes).

**Manual scenarios (all verified during /do on an isolated `127.0.0.1:9100` run, off `dokploy-network`):**

1. `GET /alive` → 200.
2. `GET /` → 200, registration page (signups on).
3. `GET /admin` with empty token → 200 "admin panel is disabled".
4. `GET /admin` with token set → 200 token-entry login form.
5. `down && up` on `vaultwarden_data` → SQLite db persists (same size + mtime).

### Out of scope

- No `mcp-vaultwarden` bridge (no Hermes integration) — deferred by task decision.
- No PostgreSQL/Redis wiring — embedded SQLite only.
- No Traefik labels (managed in Dokploy UI, not compose).

## Commits

| Hash      | Description                                          |
| --------- | --------------------------------------------------- |
| `2c6df49` | feat: add vaultwarden service and volume            |
| `686edd0` | feat: document vaultwarden env vars                 |
| `e5a6747` | docs: add vaultwarden to CONTEXT                    |
| `e020186` | fix: correct ADMIN_TOKEN hash command               |
| `3011f38` | fix: fix 2 review issues (memory 192M, https note)  |

## Changed Files

| File                              | +/-    | Description                                              |
| --------------------------------- | ------ | ------------------------------------------------------- |
| docker-compose.yml                | +37    | `vaultwarden` service (1.36.0-alpine, port 80, 192M) + volume |
| .env.example                      | +14/-3 | Vaultwarden section + 9100 in the in-use ports note     |
| services/vaultwarden/.env.example | +19    | Per-service env doc mirroring Linkding                  |
| CONTEXT.md                        | +7/-3  | Service Images + totals→13, Architecture Split, Routing |

## Issues Found

| Severity | Score | Category    | File:line                          | Description                                                                 |
| -------- | ----- | ----------- | ---------------------------------- | --------------------------------------------------------------------------- |
| Minor    | 42    | reliability | docker-compose.yml (memory)        | 128M tight vs server-side Argon2id `ADMIN_TOKEN` verify (~64 MiB spike) on no-swap Pi |
| Minor    | 25    | docs        | docker-compose.yml / .env.example  | `DOMAIN` placeholder `http://`; production needs `https://` for WebAuthn     |

## Fixed Issues

| Issue                          | Commit    | Description                                              |
| ------------------------------ | --------- | ------------------------------------------------------- |
| Memory limit tight for Argon2  | `3011f38` | Raised 128M → 192M with an explanatory comment          |
| `http://` DOMAIN, no https note| `3011f38` | Comment now states production needs https (3 files)     |

## Skipped Issues

**All found issues were fixed.**

## Recommendations

- Generate the production `ADMIN_TOKEN` with the documented `docker run --rm -it vaultwarden/server /vaultwarden hash` and store it only in Dokploy → Environment.
- Set `VAULTWARDEN_DOMAIN=https://passwords.<real-domain>` in Dokploy and add the Traefik route for that subdomain before first login.
- Consider closing `SIGNUPS_ALLOWED` after registering your account if the open-signup window is no longer needed.
