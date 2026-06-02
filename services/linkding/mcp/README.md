# `linkding/mcp` — Linkding MCP server

Native MCP server that exposes Linkding bookmarks to the AI agent **Hermes**.
Wraps [`chickenzord/linkding-mcp`](https://github.com/chickenzord/linkding-mcp)
(Go, 3 tools), served over **streamable-HTTP**. See
[`docs/mcp/CONVENTIONS.md`](../../../docs/mcp/CONVENTIONS.md) and
[ADR 0007](../../../docs/adr/0007-mcp-integration-topology.md).

## Why we build from source

The official image `ghcr.io/chickenzord/linkding-mcp` hardcodes `GOARCH=amd64`
in its Dockerfile, so the published **`arm64` tag actually contains an x86-64
binary** and dies on the Raspberry Pi (ARM64) with `exec format error`. This
[`Dockerfile`](./Dockerfile) clones the upstream source at a pinned tag and
builds for the native architecture (`TARGETARCH`). Revisit the official image
once upstream fixes the build.

## Tools

| Tool               | Purpose                                            |
| ------------------ | -------------------------------------------------- |
| `search_bookmarks` | Find bookmarks by query (optional limit)           |
| `create_bookmark`  | Add a bookmark (url + optional title, desc, tags)  |
| `get_tags`         | List available tags (optional limit)               |

AI summaries / auto-tagging happen on the Hermes side when saving — not here.

## Environment variables

The upstream binary reads exactly three env vars (`cmd/linkding-mcp/main.go`):

| Variable             | Required | Default  | Meaning                                        |
| -------------------- | -------- | -------- | ---------------------------------------------- |
| `LINKDING_URL`       | ✅ yes   | —        | Base URL of the Linkding instance              |
| `LINKDING_API_TOKEN` | ✅ yes   | —        | Linkding REST API token                        |
| `BIND_ADDR`          | no       | `:8080`  | HTTP listen address                            |

If `LINKDING_URL` or `LINKDING_API_TOKEN` is empty, the server exits with an
error — the token is mandatory.

### How the Blueprint maps them

In the root [`docker-compose.yml`](../../../docker-compose.yml) the `mcp-linkding`
service sets the image env from Blueprint conventions:

| Image env            | Value in compose                | Source                                    |
| -------------------- | ------------------------------- | ----------------------------------------- |
| `LINKDING_URL`       | `http://linkding:9090`          | fixed internal hostname (not public)      |
| `LINKDING_API_TOKEN` | `${LINKDING_MCP_TOKEN:-}`       | root `.env` → `LINKDING_MCP_TOKEN`        |
| `BIND_ADDR`          | `:8000`                         | fixed — Blueprint MCP port convention     |

So the only value you set in the root `.env` is **`LINKDING_MCP_TOKEN`**
(`LINKDING_MCP_PORT` is an optional local-test host port). Both keys are listed
in [`.env.example`](../../../.env.example) under the "MCP layer" section.

## Setup

1. **Generate the Linkding API token.** Open the Linkding UI →
   *Settings → Integrations → REST API* → copy the token. (Linkding must be
   running and a superuser created — see [`../.env.example`](../.env.example).)

2. **Put the token in the root `.env`:**

   ```dotenv
   LINKDING_MCP_TOKEN=<token-from-linkding-ui>
   ```

   On Dokploy, set it in *Environment* instead of committing it.

3. **Build and start the container:**

   ```bash
   docker compose up -d --build mcp-linkding
   ```

4. **Register the subdomain in the Dokploy UI:**
   `mcp-linkding.dashboard.example.com` → container port `8000`. Do **not** add
   Traefik labels to compose (routing is owned by Dokploy UI).

5. **Connect Hermes** to the streamable-HTTP endpoint:
   `https://mcp-linkding.dashboard.example.com/mcp`
   (the go-sdk handler answers on any path; `/mcp` is the convention). Network
   protection is Tailscale — the endpoint has no auth of its own.

## Local testing

```bash
# Build + run just this MCP, publishing the container port to localhost:8100
LINKDING_MCP_PORT=8100 docker compose up -d --build linkding mcp-linkding

# MCP handshake — expect HTTP 200, an Mcp-Session-Id header, and serverInfo
curl -s -D - -X POST http://localhost:8100/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
```

Reuse the returned `Mcp-Session-Id` header on a follow-up `tools/list` call to
see `search_bookmarks`, `create_bookmark`, `get_tags`.

## Upgrading

Bump the `VERSION` build-arg of the `mcp-linkding` service in
`docker-compose.yml` (git release tags carry the `v` prefix, e.g. `v0.1.6`),
then `docker compose build mcp-linkding`.
