# BeaverHabits FastMCP server — implementation plan

**Task:** docs/ai/16-beaverhabits-fastmcp/16-beaverhabits-fastmcp-task.md
**Complexity:** medium
**Mode:** sub-agents
**Parallel:** true

## Design decisions

### DD-1: Async HTTP client — httpx

**Decision:** Call the BeaverHabits REST API with `httpx.AsyncClient`.
**Rationale:** FastMCP tool handlers are async coroutines; a sync client (`requests`) would block the event loop. `httpx` is the de-facto async HTTP client and pairs cleanly with FastMCP.
**Alternative:** `requests` — synchronous, blocks the server's loop under concurrent calls.

### DD-2: Auth — lazy login with cached bearer token, re-login on 401

**Decision:** On the first API call, `POST {base}/auth/login` with `grant_type=password&username=<email>&password=<password>` (form-encoded), cache `access_token`. Re-login transparently when a call returns 401.
**Rationale:** BeaverHabits has no static API token — only OAuth2 password grant (task Context; API guide). Caching avoids a login per request; the 401 path handles token expiry without manual refresh.
**Alternative:** Log in on every call — extra round-trip and load on the service for each tool invocation.

### DD-3: Health — FastMCP `custom_route` `/healthz` returning 200

**Decision:** Register a `@mcp.custom_route("/healthz", methods=["GET"])` handler returning HTTP 200 without touching BeaverHabits.
**Rationale:** The compose convention (`docs/mcp/CONVENTIONS.md:71`) health-checks a dedicated health path; FastMCP exposes `custom_route` for exactly this. A bare 200 keeps the probe independent of upstream state.
**Alternative:** Probe the `/mcp` endpoint — its status code depends on the request shape and may read as unhealthy.

### DD-4: `get_habit` derives from `list_habits`

**Decision:** Implement `get_habit(habit_id)` by fetching `GET /api/v1/habits` and filtering for the matching id; return a not-found result when absent.
**Rationale:** The BeaverHabits API guide documents no single-habit GET endpoint. Filtering the list is the only reliable path.
**Alternative:** Call an assumed `GET /habits/{id}` — undocumented, would break unpredictably.

### DD-5: Module layout — `client.py` + `server.py`

**Decision:** Put the HTTP/auth client in `services/beaverhabits/mcp/client.py` and the FastMCP app, tool definitions, and entrypoint in `server.py`.
**Rationale:** Separates the transport/auth concern (mockable in unit tests) from tool wiring, keeping each file small and testable without a live instance.
**Alternative:** Single file — workable but couples auth logic to tool registration and resists unit testing.

### DD-6: Base image `python:3.12-slim`, pip-installed pinned deps

**Decision:** Build from `python:3.12-slim`, `pip install` a pinned `fastmcp` and `httpx` from `requirements.txt`, run `python -m server` (or `python server.py`) serving streamable-HTTP on `0.0.0.0:8000`.
**Rationale:** Matches the issue's "lightweight image"; `slim` avoids musl/wheel friction that `alpine` brings to Python. Pinning every version follows `services/_mcp/Dockerfile:12`.
**Alternative:** `alpine` base — smaller, but source-builds for many Python wheels on the Pi.

## Tasks

### Task 1: Implement the FastMCP server and BeaverHabits client

- **Files:** `services/beaverhabits/mcp/client.py` (create), `services/beaverhabits/mcp/server.py` (create), `services/beaverhabits/mcp/requirements.txt` (create)
- **Depends on:** none
- **Scope:** M
- **What:** Build the async BeaverHabits API client (DD-1, DD-2) and the FastMCP app exposing the four tools plus the `/healthz` route (DD-3, DD-4, DD-5).
- **How:**
  - `client.py`: `httpx.AsyncClient` wrapper reading `BEAVERHABITS_MCP_URL` (default `http://beaverhabits:8080`), `BEAVERHABITS_MCP_EMAIL`, `BEAVERHABITS_MCP_PASSWORD` from env. `login()` posts form-encoded creds to `/auth/login`, caches the token; `request()` injects `Authorization: Bearer <token>` and re-logins once on 401.
  - `server.py`: create the FastMCP app; register tools `list_habits` (`GET /api/v1/habits`), `get_habit(habit_id)` (filter list — DD-4), `complete_habit(habit_id, date=today, done=true)` (`POST /api/v1/habits/{id}/completions` body `{date_fmt:"%d-%m-%Y", date, done}`), `get_completions(habit_id, date_start, date_end, sort="asc")` (`GET /api/v1/habits/{id}/completions`). Add `@mcp.custom_route("/healthz", ...)` → 200. Entrypoint runs `transport="streamable-http", host="0.0.0.0", port=8000` (serves `/mcp`).
  - `requirements.txt`: pin `fastmcp` and `httpx` to specific released versions.
- **Context:** task Requirements 1–3, DD-1–DD-5; BeaverHabits API guide (Materials); env namespace `.env.example:108-128`.
- **Verify:** `python -c "import ast; ast.parse(open('services/beaverhabits/mcp/server.py').read()); ast.parse(open('services/beaverhabits/mcp/client.py').read())"` — no syntax error; `grep -c '@mcp' services/beaverhabits/mcp/server.py` ≥ 5 (four tools + healthz route).

### Task 2: README with manual operational steps

- **Files:** `services/beaverhabits/mcp/README.md` (create)
- **Depends on:** none
- **Scope:** S
- **What:** Document what the operator does by hand: register the `mcp-beaverhabits.dashboard.example.com` subdomain → port `8000` in the Dokploy UI, register `https://mcp-beaverhabits.dashboard.example.com/mcp` in Hermes, and verify by completing a habit from Hermes.
- **How:** Follow the layout of `services/_mcp/README.md` (what it is / env keys / manual subdomain registration / verify). State that BeaverHabits is native FastMCP (no bridge) and lists the four tools. Note creds live in root `.env` under `BEAVERHABITS_MCP_*`.
- **Context:** task Requirement 7; `services/_mcp/README.md`; `docs/mcp/CONVENTIONS.md:34-45`.
- **Verify:** `grep -q 'Dokploy' services/beaverhabits/mcp/README.md && grep -q '/mcp' services/beaverhabits/mcp/README.md` — both present.

### Task 3: Dockerfile

- **Files:** `services/beaverhabits/mcp/Dockerfile` (create)
- **Depends on:** Task 1
- **Scope:** S
- **What:** Build the lightweight Python image that installs the pinned deps and runs the server on `8000` (DD-6).
- **How:** `FROM python:3.12-slim` (pinned digest/tag), copy `requirements.txt`, `pip install --no-cache-dir -r requirements.txt`, copy `client.py`+`server.py`, `EXPOSE 8000`, `CMD` runs the server. No `:latest`.
- **Context:** Task 1 output (entrypoint name, requirements.txt); `services/_mcp/Dockerfile` for pinning discipline.
- **Verify:** `docker build -t mcp-beaverhabits-test services/beaverhabits/mcp` — builds successfully.

### Task 4: Compose service block and .env.example keys

- **Files:** `docker-compose.yml` (edit — add `mcp-beaverhabits` block near the other service blocks), `.env.example` (edit — BeaverHabits section `:102` and MCP section `:115-128`)
- **Depends on:** Task 3
- **Scope:** M
- **What:** Add the native `mcp-beaverhabits` service (Requirement 5) and the env keys (Requirement 6).
- **How:**
  - Compose block modeled on the native Firefly snippet (`docs/mcp/CONVENTIONS.md:80`): `build: { context: ./services/beaverhabits/mcp }`, `restart: unless-stopped`, `depends_on: { beaverhabits: { condition: service_started } }`, `environment:` mapping `BEAVERHABITS_MCP_URL`/`EMAIL`/`PASSWORD` (default URL `http://beaverhabits:8080`), `expose: ["8000"]`, `ports: ["${BEAVERHABITS_MCP_PORT:-}:8000"]`, healthcheck wget `http://localhost:8000/healthz`, `deploy.resources.limits.memory: 128M`, `networks: [internal, dokploy-network]`. No Traefik labels.
  - `.env.example`: add `BEAVERHABITS_MCP_EMAIL=`, `BEAVERHABITS_MCP_PASSWORD=`, `BEAVERHABITS_MCP_URL=http://beaverhabits:8080`; add a comment at `BEAVERHABITS_MCP_TOKEN` that it is unused (BeaverHabits has no static token).
- **Context:** task Requirements 5–6, Constraints; `docs/mcp/CONVENTIONS.md:76-108`; `docker-compose.yml:454-483`; `.env.example:102-128`.
- **Verify:** `docker compose config >/dev/null` — succeeds; `docker compose config | grep -A30 'mcp-beaverhabits:' | grep -E 'memory|8000|internal'` shows the limit, port, network; `grep -q '^BEAVERHABITS_MCP_EMAIL=' .env.example`.

### Task 5: Validation

- **Files:** —
- **Depends on:** all
- **Scope:** S
- **What:** Run full validation: compose config lint, image build, and a live `/healthz` probe.
- **Context:** —
- **Verify:** `docker compose config >/dev/null && docker compose build mcp-beaverhabits && BEAVERHABITS_MCP_PORT=8090 docker compose up -d mcp-beaverhabits && sleep 5 && wget -qO- http://localhost:8090/healthz && docker compose down` — config valid, build green, `/healthz` returns 200.

## Execution

- **Mode:** sub-agents
- **Parallel:** true
- **Reasoning:** Five tasks across one codebase with an independent docs task that runs alongside the server work, then a strict build → compose → validate chain.
- **Order:**
  Group 1 (parallel): Task 1, Task 2
  ─── barrier ───
  Group 2 (sequential): Task 3 → Task 4 → Task 5

## Verification

- `docker compose config` → succeeds, shows `mcp-beaverhabits` on networks `internal` + `dokploy-network`, `expose: 8000`, no Traefik labels, `memory: 128M`.
- `docker compose build mcp-beaverhabits` → image builds with the pinned Python base and pinned FastMCP version.
- `BEAVERHABITS_MCP_PORT=8090 docker compose up -d mcp-beaverhabits` then `wget -qO- http://localhost:8090/healthz` → HTTP 200.
- With valid `BEAVERHABITS_MCP_EMAIL`/`BEAVERHABITS_MCP_PASSWORD`, an MCP client (or curl against `/mcp`) lists the four tools; `list_habits` returns the account's habits; `complete_habit` against a known habit id returns `{day, done: true}`; `get_completions` then includes that date.
- Edge case: an expired/invalid cached token triggers a transparent re-login (a second call after token expiry still succeeds), and a wrong-credentials login surfaces a clear error rather than a silent empty result.
- Edge case: `get_habit` with an unknown `habit_id` returns a not-found result, not a crash.
- `grep -n BEAVERHABITS_MCP .env.example` → shows `EMAIL`, `PASSWORD`, `URL`, and the `TOKEN` "unused" comment.

## Materials

- [Issue #16 — [beaverhabits] Свой FastMCP](https://github.com/prineycom/svc-personal-dashboard/issues/16)
- [BeaverHabits API How-to Guide](https://github.com/daya0576/beaverhabits/wiki/Beaver-Habit-Tracker-API-How%E2%80%90to-Guide)
- `docs/mcp/CONVENTIONS.md` — MCP layer conventions (native vs bridge, placement, routing, secrets, compose snippets)
- `docs/adr/0007-mcp-integration-topology.md` — MCP integration topology decision
- `services/_mcp/README.md`, `services/_mcp/Dockerfile` — bridge reference (pinning/healthcheck discipline)
- `docker-compose.yml:454` — existing `beaverhabits` service block
- `.env.example:102-128` — BeaverHabits + MCP-layer env placeholders
- Epic: #9 · Depends on: #10
