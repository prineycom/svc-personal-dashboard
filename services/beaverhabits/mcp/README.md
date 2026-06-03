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

| Tool | Arguments | What it does |
|------|-----------|--------------|
| `list_habits` | — | List habits (`id` + `name`). |
| `get_habit` | `habit_id` | Return a single habit by id; `{found: false, …}` when absent. |
| `complete_habit` | `habit_id`, `date?` (`DD-MM-YYYY`, default today), `done?` (default `true`) | Mark a habit done or undone for a date. |
| `get_completions` | `habit_id`, `date_start`, `date_end`, `sort?` (default `asc`) | List a habit's completion dates over a range. |

## Environment variables

All config lives in the **root `.env`** under the `BEAVERHABITS_MCP_*` namespace
and is injected through the compose `environment:` block. `.env.example` carries
empty placeholders — never commit real secrets.

| Env var | Required | Default | Purpose |
|---------|----------|---------|---------|
| `BEAVERHABITS_MCP_EMAIL` | **yes** | — | Account email; the OAuth2 `username` the MCP logs in with. |
| `BEAVERHABITS_MCP_PASSWORD` | **yes** | — | Account password for the OAuth2 password grant. |
| `BEAVERHABITS_MCP_URL` | no | `http://beaverhabits:8080` | Internal upstream base URL. Override only if BeaverHabits runs elsewhere. |
| `BEAVERHABITS_MCP_PORT` | no | _(empty)_ | Host port for the local-test escape hatch (`${…}:8000`). Leave empty on Dokploy. |
| `BEAVERHABITS_MCP_TOKEN` | no (unused) | — | Ignored. BeaverHabits has no static API token; kept only for namespace symmetry. |

BeaverHabits authenticates with **OAuth2 password grant**: on the first tool call
the server `POST`s the email + password to `/auth/login`, caches the bearer
token, and transparently re-logs-in once on a `401`. There is no static API
token — `BEAVERHABITS_MCP_EMAIL` + `BEAVERHABITS_MCP_PASSWORD` are mandatory.

## Setup

### 1. Create the BeaverHabits account the MCP will use

The MCP logs in as a real BeaverHabits user. Pick one of:

- **UI** — open the BeaverHabits site and sign up.
- **API** — register directly:

  ```sh
  curl -X POST http://<beaverhabits-host>/auth/register \
    -H 'Content-Type: application/json' \
    -d '{"email":"hermes@example.com","password":"<strong-password>"}'
  ```

Use a dedicated account for the agent rather than your personal login.

### 2. Fill in the root `.env`

```dotenv
BEAVERHABITS_MCP_EMAIL=hermes@example.com
BEAVERHABITS_MCP_PASSWORD=<strong-password>
# BEAVERHABITS_MCP_URL=http://beaverhabits:8080   # only if you need to override
# BEAVERHABITS_MCP_PORT=8090                       # only for local testing
```

### 3. Build and start the container

```sh
docker compose up -d --build mcp-beaverhabits
```

Compose builds [`services/beaverhabits/mcp`](.) and starts the service on the
`internal` + `dokploy-network` networks. The healthcheck probes `/healthz` and the
container reports `healthy` within ~20 s.

### 4. Register the subdomain in the Dokploy UI

Map `mcp-beaverhabits.dashboard.example.com` → container port `8000`. Do **not**
add Traefik labels to `docker-compose.yml` — routing is configured in the Dokploy
UI for every service. Access is protected by Tailscale, not by auth on the
endpoint.

### 5. Register the endpoint in Hermes

Add `https://mcp-beaverhabits.dashboard.example.com/mcp` as an MCP server.

### 6. Verify end-to-end

Ask Hermes to complete a habit, then confirm the completion shows up in the
BeaverHabits UI.

## Local testing

```sh
# 1. set a host port in the root .env, e.g. BEAVERHABITS_MCP_PORT=8090
docker compose up -d --build mcp-beaverhabits

# 2. health probe
wget -qO- http://localhost:8090/healthz        # -> ok

# 3. exercise the tools over the MCP protocol (fastmcp ships inside the image)
docker compose exec -T mcp-beaverhabits python - <<'PY'
import asyncio, datetime
from fastmcp import Client
async def main():
    today = datetime.date.today().strftime("%d-%m-%Y")
    async with Client("http://localhost:8000/mcp") as c:
        print([t.name for t in await c.list_tools()])
        r = await c.call_tool("list_habits", {})
        print([b.text for b in r.content])
        # hid = "<id-from-list_habits>"
        # await c.call_tool("complete_habit", {"habit_id": hid, "date": today})
asyncio.run(main())
PY
```

> **Pi gotcha — shared `dokploy-network`.** If a production stack is already
> running on the Pi, its `beaverhabits` service shares the external
> `dokploy-network` under the same alias, so the hostname `beaverhabits` resolves
> to **both** containers via DNS round-robin and login intermittently fails
> (`LOGIN_BAD_CREDENTIALS`) against the instance that lacks your account. For a
> deterministic local test, give the test stack alternate host ports and run a
> one-off MCP container attached to the project's `…-internal` network only, where
> the service name is unique.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Tool calls raise `BeaverHabits login failed with HTTP 400 … LOGIN_BAD_CREDENTIALS` | Wrong `BEAVERHABITS_MCP_EMAIL`/`PASSWORD`, or (locally) the `dokploy-network` collision above. | Verify the account logs in via `POST /auth/login`; isolate the test stack on `…-internal`. |
| Tool calls raise `… credentials are not configured` | `BEAVERHABITS_MCP_EMAIL`/`PASSWORD` empty in `.env`. | Set both, then `docker compose up -d mcp-beaverhabits` to recreate with the new env. |
| Container stuck `unhealthy` | `/healthz` not reachable. | Check logs: `docker compose logs mcp-beaverhabits`; confirm the server bound to `0.0.0.0:8000`. |
| Hermes can't reach the server | Subdomain not mapped, or not on Tailscale. | Re-check the Dokploy subdomain → port `8000` mapping and the Tailscale connection. |
