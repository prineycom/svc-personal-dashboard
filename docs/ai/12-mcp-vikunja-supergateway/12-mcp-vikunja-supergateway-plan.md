# Add the Vikunja MCP server (supergateway bridge) — implementation plan

**Task:** docs/ai/12-mcp-vikunja-supergateway/12-mcp-vikunja-supergateway-task.md
**Complexity:** simple
**Mode:** inline
**Parallel:** false

## Design decisions

### DD-1: Reuse the shared bridge image via build-args, no new Dockerfile

**Decision:** Reference `services/_mcp/Dockerfile` from the new service with
`build.context: ./services/_mcp` and `args.MCP_PKG: "@democratize-technology/vikunja-mcp@0.2.0"`.
**Rationale:** `services/_mcp/Dockerfile:24-46` is already a parameterized
supergateway stdio→HTTP bridge driven by build-arg `MCP_PKG`; the ticket's "own
Dockerfile" requirement is met by referencing it.
**Alternative:** A per-service Dockerfile — rejected; it duplicates the bridge
and breaks the single-source convention in `services/_mcp/README.md`.

### DD-2: Copy the canonical compose block verbatim

**Decision:** Insert the `mcp-vikunja` block from `docs/mcp/CONVENTIONS.md:110-142`
unchanged (env `VIKUNJA_URL: http://vikunja:3456`, `VIKUNJA_API_TOKEN: ${VIKUNJA_MCP_TOKEN:-}`,
`expose 8000`, `ports ${VIKUNJA_MCP_PORT:-}:8000`, `wget /healthz` healthcheck,
`memory 128M`, networks `internal` + `dokploy-network`).
**Rationale:** The conventions doc is the normative spec and already carries the
reviewed block; the npm package reads exactly `VIKUNJA_URL` + `VIKUNJA_API_TOKEN`
(confirmed against the registry), so no mapping change is needed.
**Alternative:** Hand-author a fresh block — rejected; it risks drifting from
the convention and re-introduces the env-name question already resolved.

### DD-3: Routing in the Dokploy UI, documented — not in compose

**Decision:** Add the `mcp-vikunja` row to the README Step 6 domain table and
document the Hermes/verify steps; add no `traefik.*` labels to compose.
**Rationale:** `README.md:231-235` records that dual domain definition disables
the Traefik router; routing is a UI-only single source.
**Alternative:** Traefik labels in compose — rejected; it breaks the router.

## Tasks

### Task 1: Add the `mcp-vikunja` service to docker-compose.yml

- **Files:** `docker-compose.yml:131` (edit — insert a new service block directly
  after the `vikunja` block, before the Firefly III section at line 133)
- **Depends on:** none
- **Scope:** S
- **What:** Add the `mcp-vikunja` bridge service that wraps
  `@democratize-technology/vikunja-mcp@0.2.0` with the shared supergateway image.
- **How:** Copy the block from `docs/mcp/CONVENTIONS.md:110-142` verbatim:
  `build.context: ./services/_mcp` + `args.MCP_PKG: "@democratize-technology/vikunja-mcp@0.2.0"`,
  `restart: unless-stopped`, `depends_on: vikunja (condition: service_healthy)`,
  `environment: VIKUNJA_URL: http://vikunja:3456` and
  `VIKUNJA_API_TOKEN: ${VIKUNJA_MCP_TOKEN:-}`, `expose: "8000"`,
  `ports: - ${VIKUNJA_MCP_PORT:-}:8000`, the
  `["CMD","wget","-qO-","http://localhost:8000/healthz"]` healthcheck
  (interval 30s, timeout 5s, retries 5, start_period 20s),
  `deploy.resources.limits.memory: 128M`, and `networks: internal, dokploy-network`.
  Match the indentation of the surrounding `vikunja` block. Add no `traefik.*`
  labels. Confirm `.env.example:115,123` already declare `VIKUNJA_MCP_TOKEN=` and
  `VIKUNJA_MCP_PORT=`; add them only if absent.
- **Context:** `docker-compose.yml:88-131` (vikunja block + indentation),
  `docker-compose.yml:535-540` (network names), `docs/mcp/CONVENTIONS.md:110-145`
  (canonical block + env-name note), `services/_mcp/Dockerfile:18-46` (build-args).
- **Verify:** `docker compose config` — parses cleanly and lists the `mcp-vikunja`
  service with both networks, the env vars, and the healthcheck resolved.

### Task 2: Document domain registration and verification in README

- **Files:** `README.md:239-246` (edit — Step 6 domain table),
  `README.md:260-273` (edit — Step 8 verification)
- **Depends on:** none
- **Scope:** S
- **What:** Add the `mcp-vikunja` routing row and document the MCP/Hermes
  verification and Vikunja API-token source.
- **How:** Add a table row to Step 6:
  `mcp-vikunja` | `mcp-vikunja.dashboard.example.com` | `8000` | `web`, HTTPS off.
  In Step 8, document the deploy-time MCP check (probe `/healthz` → `200` and
  `/mcp` on the running container) and the Hermes acceptance step (create then
  read a Vikunja task through `https://mcp-vikunja.dashboard.example.com/mcp`).
  Note the Vikunja **API token** is generated in the Vikunja UI
  (Settings → API tokens) and stored in `.env` as `VIKUNJA_MCP_TOKEN` — distinct
  from `VIKUNJA_SERVICE_SECRET`.
- **Context:** `README.md:229-251` (Step 6 table + UI-routing rule),
  `README.md:260-273` (Step 8 verify loop), `README.md:49-68` (MCP layer overview,
  already lists `mcp-vikunja`).
- **Verify:** `grep -n "mcp-vikunja" README.md` — shows the new Step 6 row with
  host `mcp-vikunja.dashboard.example.com` and port `8000`.

### Task 3: Validation

- **Files:** —
- **Depends on:** Task 1, Task 2
- **Scope:** S
- **What:** Validate compose syntax and the bridge image build.
- **Context:** —
- **Verify:** `docker compose config` — parses and renders `mcp-vikunja`; and
  `docker build --build-arg MCP_PKG=@democratize-technology/vikunja-mcp@0.2.0 -t mcp-bridge-test services/_mcp`
  — builds successfully (needs network for the `npm install -g`).

## Execution

- **Mode:** inline
- **Parallel:** false
- **Reasoning:** Three small tasks touching two distinct files with the design
  fully specified — sequential inline execution is simplest and needs no agents.
- **Order:**
  Task 1 → Task 2 → Task 3

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
