# `opentickly/mcp` — native FastMCP for OpenTickly

Own Python + [FastMCP](https://github.com/jlowin/fastmcp) server that exposes
**OpenTickly** (Toggl-compatible time tracker) to the AI agent **Hermes** over
**streamable-HTTP**. Built per [`docs/mcp/CONVENTIONS.md`](../../../docs/mcp/CONVENTIONS.md)
and [ADR 0007](../../../docs/adr/0007-mcp-integration-topology.md); the
fork-vs-own decision is recorded in
[`docs/ai/17-opentickly-fastmcp/…-spike.md`](../../../docs/ai/17-opentickly-fastmcp/17-opentickly-fastmcp-spike.md).

Native (no bridge): the server listens on port `8000`, serves MCP at `/mcp` and
health at `/healthz`. It calls OpenTickly over the `internal` network at
`http://opentickly:8080` — never the public URL.

## Tools

| Tool | Toggl API | Arguments | What it does |
|------|-----------|-----------|--------------|
| `start_timer` | Track v9 `POST /workspaces/{wid}/time_entries` | `description` (req), `project_id`, `tags` | Start a running entry. |
| `stop_timer` | Track v9 `PATCH …/time_entries/{id}/stop` | `time_entry_id` (opt) | Stop an entry; with no id, stops the current one. |
| `list_time_entries` | Track v9 `GET /me/time_entries` | `start_date`, `end_date` (opt) | List entries, optionally in a date range. |
| `get_report` | Reports v3 `POST /workspace/{wid}/search/time_entries` | `start_date`, `end_date` (req) | Time-entry report for a date range. |

Dates are ISO-8601 (`YYYY-MM-DD`). Tool errors (upstream unreachable, auth
failure, no running timer) are returned as `{"error": …}` / `{"message": …}` —
the server never crashes on a bad upstream response.

## Environment variables

The server reads these at the **first tool call** (lazy — importing or starting
the process needs nothing, so health checks and CI work without a token):

| Server var | Required | Default | Meaning |
|------------|----------|---------|---------|
| `TOGGL_API_TOKEN` | ✅ (at first tool call) | — | OpenTickly API token (Toggl-style). Auth is HTTP Basic `token:api_token`. |
| `OPENTICKLY_BASE_URL` | — | `http://opentickly:8080` | Internal upstream base URL. |
| `OPENTICKLY_WORKSPACE_ID` | — | resolved from `/api/v9/me` | Pin a workspace; skips the per-call `GET /me` lookup. |

In the Blueprint you **do not set the server vars directly** — they are mapped by
`docker-compose.yml` from the `OPENTICKLY_MCP_*` keys in the **root `.env`**:

| Root `.env` key | → compose maps to | Required | Notes |
|-----------------|-------------------|----------|-------|
| `OPENTICKLY_MCP_TOKEN` | `TOGGL_API_TOKEN` | ✅ | OpenTickly API token (see below). |
| `OPENTICKLY_MCP_WORKSPACE_ID` | `OPENTICKLY_WORKSPACE_ID` | — | Optional; empty = default workspace. |
| `OPENTICKLY_MCP_PORT` | host side of `ports:` | — | Local-test host port only; empty on Dokploy. |

`OPENTICKLY_BASE_URL` is hard-set to `http://opentickly:8080` in compose.

### Getting the OpenTickly API token

1. Open the OpenTickly web UI and sign in (or register the first account).
2. Go to **Profile → API token** and copy the token.
3. Put it in the **root** `.env`:
   ```dotenv
   OPENTICKLY_MCP_TOKEN=<paste the token>
   ```

## Deploy (Dokploy / production)

1. In the **root `.env`** set at least `OPENTICKLY_MCP_TOKEN` (and optionally
   `OPENTICKLY_MCP_WORKSPACE_ID`). All keys are documented in the root
   `.env.example` and `services/opentickly/.env.example`.
2. Deploy the stack — compose builds the `mcp-opentickly` image and starts it
   after `opentickly` is healthy. Verify health:
   ```bash
   docker compose up -d opentickly mcp-opentickly
   docker compose ps          # mcp-opentickly should be "healthy"
   ```
3. In the **Dokploy UI**, register the subdomain
   `mcp-opentickly.dashboard.example.com` → container port `8000`.
   **Do not add Traefik labels to compose** — routing comes from the Dokploy UI.
4. Point Hermes at `https://mcp-opentickly.dashboard.example.com/mcp`.
   Health is at `/healthz`. Network protection is Tailscale; the endpoint has no
   auth of its own.

## Local development

```bash
cd services/opentickly/mcp
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

ruff check .          # lint
ruff format .         # format
pytest                # smoke tests (mocked HTTP, no network)

# Run against a local OpenTickly (e.g. exposed on host port 8082):
TOGGL_API_TOKEN=<token> OPENTICKLY_BASE_URL=http://localhost:8082 opentickly-mcp
# -> serves http://0.0.0.0:8000/mcp  (health: /healthz)
```

### Verify end to end (local Docker)

```bash
# Bring up the upstream + the MCP with a real token:
POSTGRES_PASSWORD=… OPENTICKLY_PORT=18082 OPENTICKLY_MCP_PORT=18080 \
  OPENTICKLY_MCP_TOKEN=<token> \
  docker compose up -d --build opentickly mcp-opentickly

curl -s -o /dev/null -w '%{http_code}\n' http://localhost:18080/healthz   # 200
```

Then connect any MCP client to `http://localhost:18080/mcp`, list tools, and
call `start_timer` / `list_time_entries` / `get_report`.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| Tool returns `{"error": "… 403 …"}` | Bad or missing token. Set a valid `OPENTICKLY_MCP_TOKEN` (OpenTickly Profile → API token). |
| Tool returns `{"error": "… no default_workspace_id …"}` | Account has no default workspace. Set `OPENTICKLY_MCP_WORKSPACE_ID`. |
| `{"message": "no running timer to stop"}` | `stop_timer` with no active entry — expected, not an error. |
| Container not `healthy` | `opentickly` not healthy yet, or `/healthz` unreachable. Check `docker logs mcp-opentickly`. The healthcheck uses Python (the slim image has no `wget`/`curl`). |
| `get_report` empty / fails | Confirm the OpenTickly build serves Reports API v3 (`/reports/api/v3/...`). |
