# `mcp-beaverhabits` — native BeaverHabits MCP server

A native **Python + FastMCP** server that exposes BeaverHabits to the Hermes AI
agent over **streamable-HTTP**. Unlike the bridged MCPs in
[`services/_mcp`](../../_mcp/README.md), this is **not** a supergateway bridge:
BeaverHabits is a native FastMCP server with its own image
([ADR 0007](../../../docs/adr/0007-mcp-integration-topology.md), line 41).

The container listens on port `8000` and serves:

- streamable-HTTP at `/mcp` (the URL Hermes connects to);
- health at `/healthz` (returns HTTP 200 without touching BeaverHabits).

It calls BeaverHabits over the `internal` Docker network at
`http://beaverhabits:8080`, never via the public URL. See the routing table in
[`docs/mcp/CONVENTIONS.md`](../../../docs/mcp/CONVENTIONS.md).

## Tools

| Tool | What it does |
|------|--------------|
| `list_habits` | List habits (`id` + `name`). |
| `get_habit` | Return a single habit by id. |
| `complete_habit` | Mark a habit done (or undone) for a date. |
| `get_completions` | List a habit's completions over a date range. |

## Configuration

Credentials live in the **root `.env`** under the `BEAVERHABITS_MCP_*`
namespace and are injected via the compose `environment:` block. `.env.example`
carries empty placeholders only — never commit real secrets.

| Env var | Purpose | Default |
|---------|---------|---------|
| `BEAVERHABITS_MCP_EMAIL` | Login username for the OAuth2 password grant. | — |
| `BEAVERHABITS_MCP_PASSWORD` | Login password for the OAuth2 password grant. | — |
| `BEAVERHABITS_MCP_URL` | Internal upstream base URL. | `http://beaverhabits:8080` |
| `BEAVERHABITS_MCP_PORT` | Local-test escape hatch (`${...}:8000`); empty on Dokploy. | — |

BeaverHabits has **no static API token**, so `BEAVERHABITS_MCP_TOKEN` is unused
for this service. Authentication is OAuth2 password grant: the server calls
`POST /auth/login` with the email + password, caches the bearer token, and
re-logs in on expiry.

## Manual operational steps

These steps are **not automated** — run them by hand.

1. **Register the subdomain in the Dokploy UI.** Map
   `mcp-beaverhabits.dashboard.example.com` → container port `8000`.
   Do **not** add Traefik labels to `docker-compose.yml` — routing is configured
   in the Dokploy UI for every service.
2. **Register the endpoint in Hermes.** Add
   `https://mcp-beaverhabits.dashboard.example.com/mcp` as an MCP server.
3. **Verify end-to-end.** Complete a habit from Hermes, then confirm the
   completion shows up in the BeaverHabits UI.

## Local test

```sh
# set the escape-hatch port in the root .env, e.g. BEAVERHABITS_MCP_PORT=8090
docker compose up -d mcp-beaverhabits
wget -qO- http://localhost:8090/healthz   # -> HTTP 200
```
