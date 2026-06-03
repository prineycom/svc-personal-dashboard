# Add Vaultwarden (password manager)

**Slug:** 20-vaultwarden-password-manager
**Ticket:** https://github.com/prineycom/svc-personal-dashboard/issues/20
**Complexity:** simple
**Type:** general

## Task

Add a self-hosted Vaultwarden service to the Blueprint as a single Bitwarden-compatible container with embedded SQLite.

## Context

### Area architecture

Flat monorepo deploy: one root `docker-compose.yml` holds all 13 containers (no `include`). Shared PostgreSQL 17 + Redis live at the top; each web service joins both `internal` and `dokploy-network`, exposes no `ports:` in production (Traefik routes by subdomain via Dokploy), and carries a memory limit. SQLite-only services (Linkding, BeaverHabits) skip the DB dependency and persist to a named volume. Per-service `.env.example` files under `services/<name>/` document config for readability; the root `.env.example` is the single source pasted into Dokploy → Environment.

### Files to change

- `docker-compose.yml:470-497` — Linkding block, the template for the new `vaultwarden` service block.
- `docker-compose.yml:568-577` — `volumes:` list; add `vaultwarden_data`.
- `.env.example:93-106` — add a `Vaultwarden` section after Linkding/BeaverHabits/OpenTickly.
- `.env.example:134` — port-allocation note ("In use already: 80 443 3000 3456 4000 8001 8080 8081 8082 9090"); add 9100.
- `services/vaultwarden/.env.example` — new file, mirror `services/linkding/.env.example`.
- `CONTEXT.md:65-76` — Service Images table (+1 row, update totals to 13 containers / ~950 MB idle).
- `CONTEXT.md:96-104` — Routing table (+ `passwords.dashboard.example.com`).
- `CONTEXT.md:80-87` — Architecture Split list (+ `services/vaultwarden/`).

### Patterns to reuse

- **Linkding service block** (`docker-compose.yml:470-497`) — single SQLite container: `restart: unless-stopped`, named volume, `ports: - ${LINKDING_PORT:-}:9090` local-test pattern, `networks: [internal, dokploy-network]`, `deploy.resources.limits.memory`. Copy its shape; Vaultwarden listens on container port **80** by default, so map `${VAULTWARDEN_PORT:-}:80`.
- **Domain-pinning env pattern** — Linkding's `LD_CSRF_TRUSTED_ORIGINS` and Vikunja's `VIKUNJA_SERVICE_PUBLICURL` must match the public domain. Vaultwarden's `DOMAIN` env behaves the same; set it from `VAULTWARDEN_DOMAIN` (default `http://passwords.example.com`).
- **`services/linkding/.env.example`** — header comment, "embedded SQLite — no external DB", commented local-test port line. Mirror this structure.

### Tests

No automated test suite exists. Verification is a real container run. Prior memory: the production stack runs on the shared `dokploy-network`, so a plain `docker compose up` makes bare hostnames collide with production. Verify with an alt port and an internal-only one-off container; target is ARM64 (Pi 5).

## Requirements

1. Add a `vaultwarden` service to `docker-compose.yml` mirroring the Linkding block: pinned `vaultwarden/server:<tag>-alpine` image (verify the current stable tag on Docker Hub and confirm an ARM64/arm64 manifest exists), `restart: unless-stopped`, named volume `vaultwarden_data:/data`, `ports: - ${VAULTWARDEN_PORT:-}:80`, networks `internal` + `dokploy-network`, `deploy.resources.limits.memory: 128M`.
2. Set these env vars on the service (all `${VAR:-default}` form): `DOMAIN=${VAULTWARDEN_DOMAIN:-http://passwords.example.com}`, `SIGNUPS_ALLOWED=${VAULTWARDEN_SIGNUPS_ALLOWED:-true}`, `ADMIN_TOKEN=${VAULTWARDEN_ADMIN_TOKEN:-}`.
3. Set `SIGNUPS_ALLOWED` default to `true` (registration stays open; real protection is Tailscale). State this rationale in the `.env.example` comment.
4. Document `ADMIN_TOKEN` as an Argon2 PHC hash: include the generator command `docker run --rm vaultwarden/server vaultwarden hash` (or `vaultwarden hash` inside the container) in the `.env.example` comment, and note an empty value disables the `/admin` panel.
5. Add `vaultwarden_data` to the root `volumes:` block.
6. Add a `Vaultwarden` section to root `.env.example`: `VAULTWARDEN_DOMAIN`, `VAULTWARDEN_SIGNUPS_ALLOWED`, `VAULTWARDEN_ADMIN_TOKEN`, `VAULTWARDEN_PORT=9100`. Add `9100` to the in-use ports note.
7. Create `services/vaultwarden/.env.example` mirroring `services/linkding/.env.example` (embedded-SQLite header, the three env vars with comments, commented `VAULTWARDEN_PORT=9100` local-test line).
8. Update `CONTEXT.md`: add a Vaultwarden row to Service Images (`vaultwarden/server:<tag>-alpine`, 1 container, SQLite, ~50 MB, ARM64 ✅); bump totals to 13 containers / ~950 MB idle; add `services/vaultwarden/` to Architecture Split; add `passwords.dashboard.example.com` to Routing.
9. Verify with a real container run on an alt port (`VAULTWARDEN_PORT=9100`), isolated from the production stack per the constraint below.

## Constraints

- Keep `docker-compose.yml` one flat file — no `include`, no compose fragments under `services/`.
- Do not use `:latest`; pin an explicit image tag.
- Do not add a PostgreSQL or Redis dependency — Vaultwarden uses embedded SQLite, like Linkding and BeaverHabits.
- Do not add an MCP wrapper (`mcp-vaultwarden`) — out of scope for this task.
- Do not hardcode the real domain or any secret in git; use `${VAR:-placeholder}` defaults and `example.com` placeholders, matching the existing files.
- Do not commit a real `.env`; `.gitignore` ignores `*.env` but allows `*.env.example` — keep the new file named `.env.example`.
- For local verification, do not run a plain shared-network `docker compose up`: bare hostnames collide with the running production stack on `dokploy-network`. Use an alt port + internal-only one-off container.
- Do not change the Linkding/BeaverHabits/Vikunja blocks or any existing service config.

## Verification

- `docker compose config -q` → exits 0 (compose file parses, no undefined-var errors).
- `docker compose config | grep -A2 vaultwarden` → shows the pinned image tag, `:80` target port, and `vaultwarden_data` volume.
- Isolated run with `VAULTWARDEN_PORT=9100` on ARM64 → container reaches a healthy/running state; `curl -sf http://127.0.0.1:9100/alive` returns 200 (Vaultwarden liveness endpoint).
- With `SIGNUPS_ALLOWED=true`, the web vault at `http://127.0.0.1:9100/` serves the registration page.
- With a valid Argon2 `ADMIN_TOKEN`, `http://127.0.0.1:9100/admin` prompts for the admin token; with an empty token, `/admin` returns 404.
- `git grep -n "vaultwarden" CONTEXT.md` → Service Images, Architecture Split, and Routing all reference it; container total reads 13.
- Edge case: a redeploy preserves data — the named `vaultwarden_data` volume keeps the SQLite db across `docker compose down && up` (no bind mount to the git-clone dir).

## Materials

- [Vaultwarden — GitHub](https://github.com/dani-garcia/vaultwarden)
- [Vaultwarden — Docker Hub](https://hub.docker.com/r/vaultwarden/server)
- `docker-compose.yml` (Linkding block at lines 470-497)
- `services/linkding/.env.example`
- `.env.example` (port note at line 134)
- `CONTEXT.md` (Service Images, Architecture Split, Routing)
