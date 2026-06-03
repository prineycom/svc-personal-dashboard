# Add the Vikunja MCP server (supergateway bridge)

**Slug:** 12-mcp-vikunja-supergateway
**Ticket:** https://github.com/prineycom/svc-personal-dashboard/issues/12
**Complexity:** simple
**Type:** general

## Task

Add an `mcp-vikunja` service to `docker-compose.yml` that wraps `@democratize-technology/vikunja-mcp@0.2.0` with the existing supergateway bridge image, and document its Dokploy domain, Hermes registration, and verification.

## Context

### Area architecture

The stack runs each service as a flat entry under `services:` in a single
`docker-compose.yml`. Stage 2 adds one `mcp-<svc>` container per service that
exposes a Model Context Protocol endpoint to the external **Hermes** agent.
A stdio-only MCP server (Vikunja) is wrapped by **supergateway** into a
streamable-HTTP endpoint on port `8000` (`/mcp`) with health at `/healthz`.
The MCP reaches its service over the `internal` network; Hermes reaches the MCP
over the `dokploy-network` via the `mcp-vikunja.dashboard.example.com` subdomain,
which is registered in the **Dokploy UI** (never via `traefik.*` labels in
compose — dual definition disables the router).

Hermes lives outside this repository; "register the endpoint in Hermes" means
pointing Hermes's own config at `https://mcp-vikunja.dashboard.example.com/mcp`.
There is no Hermes service or config file in this repo — that is expected.

### Files to change

- `docker-compose.yml:88-131` — the existing `vikunja` service (internal host
  `vikunja`, port `3456`, on `internal` + `dokploy-network`). The new
  `mcp-vikunja` block lands as a sibling, directly after this block.
- `docker-compose.yml:522-540` — `volumes:` / `networks:` tail; the new service
  needs no new named volume and joins the existing `internal` + `dokploy-network`.
- `README.md:239-246` — Step 6 Dokploy domain table; add an `mcp-vikunja` row.
- `README.md:260-273` — Step 8 verification; document the MCP `/healthz` + `/mcp`
  check and the Hermes "create/read a task" acceptance step.

### Patterns to reuse

- `docs/mcp/CONVENTIONS.md:110-142` — the canonical, copy-ready `mcp-vikunja`
  compose block: `build.context: ./services/_mcp` with
  `args.MCP_PKG: "@democratize-technology/vikunja-mcp@0.2.0"`,
  `depends_on: vikunja (condition: service_healthy)`,
  `environment: VIKUNJA_URL: http://vikunja:3456` and
  `VIKUNJA_API_TOKEN: ${VIKUNJA_MCP_TOKEN:-}`, `expose: "8000"`,
  `ports: ${VIKUNJA_MCP_PORT:-}:8000`, a `wget /healthz` healthcheck,
  `memory: 128M`, and networks `internal` + `dokploy-network`. Copy it verbatim.
- `services/_mcp/Dockerfile:24-46` — the reusable supergateway bridge image,
  parameterized by build-arg `MCP_PKG`. The ticket's "own Dockerfile" requirement
  is satisfied by referencing this image; do not add a new Dockerfile.
- `docker-compose.yml:112-113` — the `${X_PORT:-}:N` empty-default local-test
  port convention; reuse as `${VIKUNJA_MCP_PORT:-}:8000`.
- `services/_mcp/README.md:24-59` — ready-to-paste block plus the routing note.

### Tests

- Coverage gap: no test framework, no CI in the repo. Per-service `healthcheck`
  blocks are the only runtime probe; "verification" is manual shell snippets.
- `docs/ai/10-mcp-conventions/10-mcp-conventions-plan.md:56` documents the bridge
  build check: `docker build --build-arg MCP_PKG=@democratize-technology/vikunja-mcp@0.2.0 -t mcp-bridge-test services/_mcp`.

## Requirements

1. Add an `mcp-vikunja` service to `docker-compose.yml` after the `vikunja`
   block (≈ line 131), copied from `docs/mcp/CONVENTIONS.md:110-142`:
   `build.context: ./services/_mcp` with
   `args.MCP_PKG: "@democratize-technology/vikunja-mcp@0.2.0"`,
   `restart: unless-stopped`, `depends_on: vikunja (service_healthy)`,
   `environment: VIKUNJA_URL: http://vikunja:3456` and
   `VIKUNJA_API_TOKEN: ${VIKUNJA_MCP_TOKEN:-}`, `expose: "8000"`,
   `ports: - ${VIKUNJA_MCP_PORT:-}:8000`, the `wget -qO- .../healthz`
   healthcheck, `deploy.resources.limits.memory: 128M`, and networks
   `internal` + `dokploy-network`.
2. Confirm the credential keys already exist in `.env.example:115,123`
   (`VIKUNJA_MCP_TOKEN=`, `VIKUNJA_MCP_PORT=`). Add them only if absent; do not
   commit any real token value.
3. Add a row to the Step 6 domain table (`README.md:239-246`):
   `mcp-vikunja` → `mcp-vikunja.dashboard.example.com` → container port `8000`,
   `web`, HTTPS off.
4. Document, in `README.md` Step 8, the MCP verification: probe
   `http://localhost:8000/healthz` and `/mcp` on the running container, and the
   Hermes acceptance step (create then read a Vikunja task through Hermes,
   pointed at `https://mcp-vikunja.dashboard.example.com/mcp`).
5. Note that the Vikunja **API token** is generated in the Vikunja UI
   (Settings → API tokens) and placed in `.env` as `VIKUNJA_MCP_TOKEN` — it is
   distinct from `VIKUNJA_SERVICE_SECRET` (`docker-compose.yml:104`).

## Constraints

- Do not add a new Dockerfile — reuse `services/_mcp/Dockerfile` via
  `build.args.MCP_PKG`.
- Do not change `services/_mcp/Dockerfile`; keep the `supergateway@3.4.0` pin
  (a bump belongs to the shared bridge image, out of scope here).
- Do not add `traefik.*` labels to `docker-compose.yml` — routing is the Dokploy
  UI only; dual definition disables the Traefik router (`README.md:231-235`).
- Do not modify the existing `vikunja` service block or any other service.
- Do not commit a real token; `VIKUNJA_MCP_TOKEN` stays empty in `.env.example`
  (`.env` and `*.env` are git-ignored).
- Pin versions — never `:latest`. The MCP package stays `@0.2.0` (confirmed
  current).
- The MCP container must join both `internal` (to reach `vikunja:3456`) and
  `dokploy-network` (so the subdomain routes); omitting either breaks it.
- Dokploy-UI domain registration, Hermes registration, and the live
  create/read check are deploy-time steps — document them, do not execute them.

## Verification

- `docker compose config` → parses cleanly and lists the `mcp-vikunja` service
  with the env, ports, healthcheck, and both networks resolved.
- `docker build --build-arg MCP_PKG=@democratize-technology/vikunja-mcp@0.2.0 -t mcp-bridge-test services/_mcp`
  → builds successfully (needs network for the `npm install -g`).
- `grep -n "mcp-vikunja" README.md` → shows the new Step 6 domain-table row
  (host `mcp-vikunja.dashboard.example.com`, port `8000`).
- Edge case: `mcp-vikunja` `depends_on` `vikunja` with `condition: service_healthy`
  so the bridge starts only after Vikunja's `doctor` healthcheck passes.
- Deploy-time (documented, not run here): the container answers `200` on
  `http://localhost:8000/healthz`, and Hermes creates and reads back a Vikunja
  task through `https://mcp-vikunja.dashboard.example.com/mcp`.

## Materials

- [Issue #12 — vikunja MCP via supergateway](https://github.com/prineycom/svc-personal-dashboard/issues/12)
- [Epic #9 — MCP integration](https://github.com/prineycom/svc-personal-dashboard/issues/9)
- [Issue #10 — MCP conventions (dependency)](https://github.com/prineycom/svc-personal-dashboard/issues/10)
- `docs/mcp/CONVENTIONS.md` — normative spec; canonical `mcp-vikunja` block at lines 110-142
- `services/_mcp/Dockerfile` — the supergateway bridge image
- `services/_mcp/README.md` — copy-ready block + registration note
- `docs/adr/0007-mcp-integration-topology.md` — bridge-vs-native decision record
- `docker-compose.yml` — vikunja block (88-131), networks (535-540)
- `.env.example` — MCP layer keys (108-128)
- `README.md` — MCP layer overview (49-68), Step 6 domains (229-251), Step 8 verify (260-273)
- npm: `@democratize-technology/vikunja-mcp@0.2.0` — reads `VIKUNJA_URL`, `VIKUNJA_API_TOKEN`
