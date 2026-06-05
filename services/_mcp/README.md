# `_mcp` — reusable MCP bridge

Shared Docker image that wraps a **stdio-only** MCP server in a
**streamable-HTTP** endpoint via [supergateway](https://github.com/supercorp-ai/supergateway).

Use this bridge when an MCP ships stdio-only, or when its official image has no
build for the target arch. MCP servers with a native-HTTP image for the target
arch run that image directly. See the routing table in
[`docs/mcp/CONVENTIONS.md`](../../docs/mcp/CONVENTIONS.md) and
[`docs/adr/0007-mcp-integration-topology.md`](../../docs/adr/0007-mcp-integration-topology.md).

## Who uses it

| MCP | Wrapped package | Bridge? |
|-----|-----------------|---------|
| Vikunja ([#12](https://github.com/prineycom/svc-personal-dashboard/issues/12)) | `@democratize-technology/vikunja-mcp` | ✅ yes |
| Wger ([#14](https://github.com/prineycom/svc-personal-dashboard/issues/14)) | `@juxsta/wger-mcp` ([setup](../wger/README.md)) | ✅ yes |
| Firefly III ([#13](https://github.com/prineycom/svc-personal-dashboard/issues/13)) | `mcp-server-firefly-iii` ([setup](../../docs/mcp/firefly-iii.md)) | ✅ yes (official image is amd64-only) |
| Linkding ([#15](https://github.com/prineycom/svc-personal-dashboard/issues/15)) | — | ❌ native HTTP image |

## How to add a bridged MCP

Add a service to the root `docker-compose.yml`:

```yaml
  mcp-vikunja:
    build:
      context: ./services/_mcp
      args:
        MCP_PKG: "@democratize-technology/vikunja-mcp@0.2.0"  # pin the version
    restart: unless-stopped
    depends_on:
      vikunja:
        condition: service_healthy
    environment:
      VIKUNJA_URL: http://vikunja:3456/api/v1   # internal host + /api/v1 (required)
      VIKUNJA_API_TOKEN: ${VIKUNJA_MCP_TOKEN:-}  # token lives in root .env
    expose:
      - "8000"
    ports:
      - ${VIKUNJA_MCP_PORT:-}:8000              # local-test escape hatch only
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 5s
      retries: 5
      start_period: 20s
    deploy:
      resources:
        limits:
          memory: 128M
    networks:
      - internal
      - dokploy-network
```

Then register the subdomain `mcp-vikunja.dashboard.example.com` → container
port `8000` **in the Dokploy UI** (do not add Traefik labels to compose). The
streamable-HTTP endpoint defaults to `/mcp`, so Hermes connects to
`https://mcp-vikunja.dashboard.example.com/mcp`; health is at `/healthz`.

The exact env-var names depend on the wrapped package — check its README and
map them onto the `<SERVICE>_MCP_*` keys in the root `.env`.

## Vikunja MCP — setup

Wraps [`@democratize-technology/vikunja-mcp`](https://www.npmjs.com/package/@democratize-technology/vikunja-mcp)
(pinned `@0.2.0`). The bridge image installs the package at build time and runs
it offline via `npx --no-install`, so a cold start never contacts the npm
registry.

### Environment variables

The container reads these (names are fixed by the package):

| Variable            | Required | Set where                | Value / format                                                                 |
|---------------------|----------|--------------------------|--------------------------------------------------------------------------------|
| `VIKUNJA_URL`       | yes      | `docker-compose.yml`     | `http://vikunja:3456/api/v1` — internal host **plus the `/api/v1` suffix**. Used verbatim; without `/api/v1` every call hits the Vikunja frontend and fails with `Unexpected token '<'`. |
| `VIKUNJA_API_TOKEN` | yes      | root `.env` (`VIKUNJA_MCP_TOKEN`) | Vikunja API token, format `tk_…`. Mapped in compose as `VIKUNJA_API_TOKEN: ${VIKUNJA_MCP_TOKEN:-}`. A JWT (`eyJ…`) also works but expires. |
| `LOG_LEVEL`         | no       | compose (optional)       | `debug` \| `info` (default) \| `warn` \| `error`.                              |
| `DEBUG`             | no       | compose (optional)       | Set to `true` for verbose diagnostics.                                         |

The token is auto-detected (`tk_` → API token, `eyJ` → JWT); no auth-type flag
is needed.

### Step-by-step

1. **Create the Vikunja API token.** Vikunja UI → **Settings → API Tokens →
   Create token**. Grant at least Tasks, Projects, and Labels (read + write).
   Copy the `tk_…` value.
2. **Put it in the root `.env`:**
   ```dotenv
   VIKUNJA_MCP_TOKEN=tk_your_real_token_here
   ```
   Never commit `.env` (it is git-ignored); the token lives only there / in
   Dokploy → Environment.
3. **Deploy.** The `mcp-vikunja` service builds from `./services/_mcp` and joins
   `internal` (reaches `vikunja:3456`) + `dokploy-network` (external routing).
4. **Register the domain** in the Dokploy UI: `mcp-vikunja.dashboard.example.com`
   → container port `8000`, entrypoint `web`. No `traefik.*` labels in compose.
5. **Register in Hermes:** point Hermes at
   `https://mcp-vikunja.dashboard.example.com/mcp`.

### Verify

```bash
# Health (supergateway is up):
docker compose exec mcp-vikunja wget -qO- http://localhost:8000/healthz   # → ok

# Tool list (MCP server starts and exposes Vikunja tools), driven over stdio:
docker compose exec -T mcp-vikunja sh -c 'printf "%s\n" \
  "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{},\"clientInfo\":{\"name\":\"v\",\"version\":\"1\"}}}" \
  "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}" \
  "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}" | vikunja-mcp'
# → serverInfo: vikunja-mcp, tools: vikunja_tasks/projects/labels/teams/
#   filters/templates/webhooks/batch_import/auth
```

A `vikunja_tasks list` call returning real tasks (not an auth error) confirms the
token end to end. `missing/invalid token` means `VIKUNJA_MCP_TOKEN` is unset or
wrong; `Unexpected token '<'` means `VIKUNJA_URL` is missing the `/api/v1` suffix.
