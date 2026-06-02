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

| Tool | Toggl API | What it does |
|------|-----------|--------------|
| `start_timer` | Track v9 `POST /workspaces/{wid}/time_entries` | Start a running entry (`description`, optional `project_id`, `tags`). |
| `stop_timer` | Track v9 `PATCH …/time_entries/{id}/stop` | Stop a running entry; with no id, stops the current one. |
| `list_time_entries` | Track v9 `GET /me/time_entries` | List entries, optionally bounded by `start_date`/`end_date`. |
| `get_report` | Reports v3 `POST /workspace/{wid}/search/time_entries` | Time-entry report for a date range. |

## Configuration

Read from the environment (injected by `docker-compose.yml`):

| Env var | Default | Meaning |
|---------|---------|---------|
| `TOGGL_API_TOKEN` | — (required at first tool call) | OpenTickly API token. Mapped from `OPENTICKLY_MCP_TOKEN` in the root `.env`. |
| `OPENTICKLY_BASE_URL` | `http://opentickly:8080` | Internal upstream base URL. |
| `OPENTICKLY_WORKSPACE_ID` | — | Optional. Falls back to the user's `default_workspace_id` from `/api/v9/me`. |

Authentication to OpenTickly is Toggl-style HTTP Basic: username = the token,
password = the literal `api_token`.

## Deploy & register in Hermes

The container is defined as `mcp-opentickly` in the root `docker-compose.yml`.

1. Set `OPENTICKLY_MCP_TOKEN` (and optionally `OPENTICKLY_MCP_PORT` for local
   testing) in the root `.env`. Both keys are in the root `.env.example`.
2. In the **Dokploy UI**, register the subdomain
   `mcp-opentickly.dashboard.example.com` → container port `8000`.
   **Do not add Traefik labels to compose** — routing comes from the Dokploy UI.
3. Connect Hermes to `https://mcp-opentickly.dashboard.example.com/mcp`.
   Health is at `/healthz`. Network protection is Tailscale; the endpoint has no
   auth of its own.

## Local development

```bash
cd services/opentickly/mcp
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

ruff check .          # lint
pytest                # smoke tests (mocked HTTP, no network)

# Run against a local OpenTickly:
TOGGL_API_TOKEN=… OPENTICKLY_BASE_URL=http://localhost:8082 opentickly-mcp
```
