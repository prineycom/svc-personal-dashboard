# Add Vaultwarden (password manager) — implementation plan

**Task:** docs/ai/20-vaultwarden-password-manager/20-vaultwarden-password-manager-task.md
**Complexity:** simple
**Mode:** inline
**Parallel:** false

## Design decisions

### DD-1: Model the service on the Linkding block, not a DB-backed service

**Decision:** Copy the shape of the Linkding service (`docker-compose.yml:470-497`) — single container, named volume, no `depends_on`, `networks: [internal, dokploy-network]`, `deploy.resources.limits.memory: 128M`.
**Rationale:** Vaultwarden uses embedded SQLite like Linkding and BeaverHabits; it needs neither PostgreSQL nor Redis. Linkding is the closest existing analog already proven on ARM64.
**Alternative:** A Postgres-backed config — rejected; adds a DB dependency the issue explicitly avoids ("init volume for SQLite, база создаётся автоматически").

### DD-2: Map the host port to container port 80

**Decision:** `ports: - ${VAULTWARDEN_PORT:-}:80`, with `VAULTWARDEN_PORT=9100` for local testing only.
**Rationale:** Vaultwarden's Rocket server listens on container port 80 by default (unlike Linkding's 9090). 9100 is free per the in-use list in `.env.example:134` (`80 443 3000 3456 4000 8001 8080 8081 8082 9090`). Empty default keeps production behind Traefik with no published port, matching every other web service.
**Alternative:** Hardcode a published port — rejected; breaks the Traefik-only production convention.

### DD-3: No healthcheck block

**Decision:** Omit `healthcheck:`, matching the Linkding block.
**Rationale:** Keeps the service minimal and avoids the "minimal image lacks wget/curl" trap that forced a custom probe on Vikunja (`docker-compose.yml:115-122`). The `/alive` endpoint is still used for manual verification.
**Alternative:** A wget-based healthcheck — rejected; unneeded for a single SQLite container and risks a false-unhealthy state.

### DD-4: Pin an explicit, ARM64-verified alpine tag

**Decision:** Pin `vaultwarden/server:<tag>-alpine`; during execution, resolve the current stable tag and confirm an arm64 manifest with `docker manifest inspect vaultwarden/server:<tag>-alpine | grep arm64`.
**Rationale:** Project convention forbids `:latest` (`docker-compose.yml:15`); the target is a Pi 5 (arm64), so the manifest must include arm64.
**Alternative:** `:latest` or an amd64-only tag — rejected; violates the pin rule and the Firefly MCP arm64 lesson.

## Tasks

### Task 1: Add the vaultwarden service and volume to docker-compose.yml

- **Files:** `docker-compose.yml:470-497` (read as template), `docker-compose.yml:531-566` (insert new block after OpenTickly), `docker-compose.yml:568-577` (edit volumes list)
- **Depends on:** none
- **Scope:** S
- **What:** Add a `vaultwarden` service block mirroring Linkding, and register the `vaultwarden_data` named volume.
- **How:** After the OpenTickly block (before the `volumes:` key), add a service `vaultwarden`: pinned `vaultwarden/server:<tag>-alpine` (resolve tag per DD-4), `restart: unless-stopped`; `environment:` with `DOMAIN: ${VAULTWARDEN_DOMAIN:-http://passwords.example.com}`, `SIGNUPS_ALLOWED: ${VAULTWARDEN_SIGNUPS_ALLOWED:-true}`, `ADMIN_TOKEN: ${VAULTWARDEN_ADMIN_TOKEN:-}`; `volumes: - vaultwarden_data:/data`; `ports: - ${VAULTWARDEN_PORT:-}:80`; `deploy.resources.limits.memory: 128M`; `networks: [internal, dokploy-network]`. Add `vaultwarden_data:` to the `volumes:` block. No healthcheck (DD-3), no `depends_on` (DD-1). Add a `# ── Vaultwarden (Passwords) ──` section comment matching the surrounding style.
- **Context:** `docker-compose.yml:470-497` (Linkding template), `docker-compose.yml:568-577` (volumes list), the task file Requirements 1-2.
- **Verify:** `docker compose config -q` — exits 0; `docker compose config | grep -A2 vaultwarden` shows the pinned image, `:80` target, and `vaultwarden_data`.

### Task 2: Add Vaultwarden env vars to root .env.example and create services/vaultwarden/.env.example

- **Files:** `.env.example:105-106` (add section after OpenTickly), `.env.example:134` (edit in-use ports note), `services/vaultwarden/.env.example` (create)
- **Depends on:** Task 1
- **Scope:** S
- **What:** Document the four Vaultwarden env vars in the root file and mirror them in a per-service `.env.example`.
- **How:** In root `.env.example`, add a `# ── Vaultwarden (Passwords) ──` section with `VAULTWARDEN_DOMAIN=http://passwords.example.com`, `VAULTWARDEN_SIGNUPS_ALLOWED=true` (comment: registration stays open; real protection is Tailscale, per DD/clarification), `VAULTWARDEN_ADMIN_TOKEN=` (comment: Argon2 PHC hash from `docker run --rm vaultwarden/server vaultwarden hash`; empty disables `/admin`), `VAULTWARDEN_PORT=9100`. Append `9100` to the in-use ports note at line 134. Create `services/vaultwarden/.env.example` mirroring `services/linkding/.env.example`: embedded-SQLite header comment, the three service env vars with the same comments, and a commented `# VAULTWARDEN_PORT=9100` local-test line. Keep var names identical to Task 1's compose references.
- **Context:** `.env.example:93-106` (Linkding/BeaverHabits/OpenTickly sections), `.env.example:134` (ports note), `services/linkding/.env.example` (mirror target), the new compose block from Task 1.
- **Verify:** `docker compose config -q` — exits 0 (every `${VAULTWARDEN_*}` resolves); `grep -c VAULTWARDEN .env.example` ≥ 4; `git status --short services/vaultwarden/.env.example` shows the new tracked-able file (not ignored).

### Task 3: Update CONTEXT.md — Service Images, Architecture Split, Routing

- **Files:** `CONTEXT.md:65-76` (Service Images table + totals), `CONTEXT.md:80-87` (Architecture Split), `CONTEXT.md:96-104` (Routing table)
- **Depends on:** Task 1
- **Scope:** S
- **What:** Record Vaultwarden across the three CONTEXT.md sections and bump the container/RAM totals.
- **How:** Add a Service Images row: `| Vaultwarden | \`vaultwarden/server:<tag>-alpine\` | 1 | SQLite | ~50 MB | ✅ |`. Change the totals line (`CONTEXT.md:76`) to 13 containers / ~950 MB idle. Add `services/vaultwarden/ — пароли (1 контейнер)` to the Architecture Split list. Add a Routing row `| Vaultwarden | \`passwords.dashboard.example.com\` |`. Use the same `<tag>` resolved in Task 1.
- **Context:** `CONTEXT.md:63-104` (the three tables/lists), the task file Requirement 8.
- **Verify:** `git grep -n vaultwarden CONTEXT.md` returns Service Images, Architecture Split, and Routing matches; `grep -n "13 контейнеров" CONTEXT.md` matches the totals line.

### Task 4: Validation

- **Files:** —
- **Depends on:** all
- **Scope:** S
- **What:** Validate config statically, then run a real isolated container on the alt port per the no-shared-network constraint.
- **How:** Run `docker compose config -q`. Resolve and pin the alpine tag (DD-4) and confirm arm64. Start an isolated, internal-only one-off container on `VAULTWARDEN_PORT=9100` (avoid joining the production `dokploy-network`; bare hostnames collide with the running prod stack). Exercise the verification endpoints below, then tear down — the named volume must survive a `down && up`.
- **Context:** the task file Verification section; memory: local-mcp-test-dns-collision, verify-mcp-at-runtime.
- **Verify:** `docker compose config -q` exits 0; on the isolated run `curl -sf http://127.0.0.1:9100/alive` returns 200; `http://127.0.0.1:9100/` serves the registration page with `SIGNUPS_ALLOWED=true`; `/admin` prompts for the token with a valid Argon2 `ADMIN_TOKEN` and returns 404 when empty; `vaultwarden_data` retains the SQLite db across `docker compose down && up`.

## Execution

- **Mode:** inline
- **Parallel:** false
- **Reasoning:** Four small config edits in one codebase with a shared env-var contract make a single sequential inline pass simplest; sub-agents would re-derive context for no parallelism gain.
- **Order:**
  Task 1 → Task 2 → Task 3 → Task 4

## Verification

- `docker compose config -q` → exits 0 (compose file parses, no undefined-var errors).
- `docker compose config | grep -A2 vaultwarden` → shows the pinned image tag, `:80` target port, and `vaultwarden_data` volume.
- Isolated run with `VAULTWARDEN_PORT=9100` on ARM64 → container reaches a healthy/running state; `curl -sf http://127.0.0.1:9100/alive` returns 200.
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
