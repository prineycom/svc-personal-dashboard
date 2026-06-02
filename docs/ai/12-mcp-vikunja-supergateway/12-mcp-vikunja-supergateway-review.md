# Code Review: 12-mcp-vikunja-supergateway

## Summary

### Context and goal

Add a Vikunja MCP server to the dashboard stack so the Hermes agent can reach
Vikunja over MCP. The stdio-only `@democratize-technology/vikunja-mcp@0.2.0` is
wrapped with the existing supergateway bridge image (`services/_mcp`) and exposed
as streamable-HTTP on port `8000`.

### Key code areas for review

1. **`docker-compose.yml:133` (`mcp-vikunja`)** — the new service: build-args, env,
   healthcheck, resource cap, and dual-network attachment. Determines whether the
   bridge reaches Vikunja and whether Traefik/Hermes can route to it.
2. **`README.md:247` (Step 6 row) + `README.md:285` (Step 8 verify)** — the routing
   contract (UI-only, no compose labels) and the deploy-time verification path.

### Complex decisions

1. **Reuse the shared bridge via `build.args.MCP_PKG`** (`docker-compose.yml:135-137`)
   — no per-service Dockerfile; the `services/_mcp` image is parameterized.
2. **`${VIKUNJA_MCP_PORT:-}:8000` empty-default** (`docker-compose.yml:151`) — host
   publish only for local testing; empty on Dokploy where routing is the subdomain.
   Mirrors the existing `vikunja` block convention.

### Questions for the reviewer

1. Are `vikunja-mcp@0.2.0` and the bridge's `supergateway@3.4.0` pins acceptable for
   this release? (0.2.0 confirmed current; supergateway latest is 3.4.3, bump
   deferred to the shared image's own scope.)

### Risks and impact

- The MCP needs a real Vikunja API token (`VIKUNJA_MCP_TOKEN`) generated in the
  Vikunja UI; with an empty token the bridge starts but Vikunja calls fail auth.
- The container must stay on both `internal` (reach `vikunja:3456`) and
  `dokploy-network` (external routing); dropping either breaks it.
- First deploy builds the image (network needed for `npm install -g`).

### Tests and manual checks

**Auto-tests:**

- None — the repo has no test framework or CI. `docker compose config` is the only
  static check.

**Manual scenarios:**

1. `docker compose config -q` → exit 0, `mcp-vikunja` rendered. ✅ verified.
2. `docker build --build-arg MCP_PKG=@democratize-technology/vikunja-mcp@0.2.0 -t mcp-bridge-test services/_mcp` → builds. ✅ verified.
3. Deploy-time: `/healthz` → `200`; create + read a Vikunja task through Hermes.

### Out of scope

- Dokploy-UI domain registration, Hermes registration, and the live create/read
  check — documented as deploy-time steps, not executed.
- Bumping `supergateway` in the shared `services/_mcp/Dockerfile`.

## Commits

| Hash      | Description                                                  |
| --------- | ------------------------------------------------------------ |
| `6c1394e` | feat(12-...): add mcp-vikunja supergateway bridge service    |
| `0d2ca48` | docs(12-...): document mcp-vikunja domain and verification   |

## Changed Files

| File                | +/-   | Description                                                  |
| ------------------- | ----- | ------------------------------------------------------------ |
| `docker-compose.yml`| +40   | New `mcp-vikunja` bridge service after the `vikunja` block   |
| `README.md`         | +19   | Step 6 domain row + MCP routing note + Step 8 bridge verify  |

## Issues Found

**Code is clean.**

The diff matches the canonical block in `docs/mcp/CONVENTIONS.md:110-142`, satisfies
all five task requirements, and honors every constraint (no new Dockerfile, no
`traefik.*` labels, `vikunja` block untouched, pinned `@0.2.0`, both networks, no
committed token).

## Fixed Issues

**All issues fixed.**

## Skipped Issues

**All found issues were fixed.**

## Recommendations

- Before merge, confirm the bridge's `supergateway@3.4.0` pin (`services/_mcp/Dockerfile:27`)
  is the intended version; 3.4.3 is available but belongs to the shared image's scope.
- At deploy, set a real `VIKUNJA_MCP_TOKEN` and complete the documented Dokploy-UI
  and Hermes registration before relying on the endpoint.

## Live verification (2026-06-02)

Ran the bridge against the live Vikunja (`vikunja:3456`, healthy) on the running
stack's `*-internal` network.

**Verified working:**

- Image builds; `docker compose config` renders `mcp-vikunja` with both networks.
- supergateway starts; `/healthz` → `ok`; container reaches `vikunja:3456/api/v1`.
- MCP `initialize` → `serverInfo: vikunja-mcp`; child logs
  `Auto-authenticating with Vikunja … Using detected auth type: api-token … server started`.
- `tools/list` exposes the full tool set: `vikunja_tasks`, `vikunja_projects`,
  `vikunja_labels`, `vikunja_teams`, `vikunja_filters`, `vikunja_templates`,
  `vikunja_webhooks`, `vikunja_batch_import`, `vikunja_auth`.

**Bug found and fixed (`996ab82`):**

- The shared bridge `CMD` used `npx -y "${MCP_PKG}"`, which contacts
  `registry.npmjs.org` on every cold start and fails on the egress-less
  `internal` network (`npm error code EAI_AGAIN`), exiting the stdio child.
  Replaced with `npx --no-install "${MCP_PKG%@*}"` so npx runs the
  globally-installed package offline. Re-verified on an **internal-only**
  network: `/healthz` ok and `tools/list` returns all tools with zero registry
  contact.

**Open robustness note (not fixed):**

- supergateway 3.4.0 stateless mode throws `No connection established for
  request ID` and exits the whole process when a child reply arrives after the
  client disconnected. `restart: unless-stopped` recovers it, and the offline
  fix removes the slow-start that mainly triggered it. Re-check against
  supergateway 3.4.3 when the shared image bumps.

**Not verified:** authenticated CRUD (create/read a task) — needs a real
`VIKUNJA_MCP_TOKEN`; testing stopped at the auth boundary by choice.
