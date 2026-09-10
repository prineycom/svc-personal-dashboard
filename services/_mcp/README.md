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
| Firefly III ([#13](https://github.com/prineycom/svc-personal-dashboard/issues/13)) | `mcp-server-firefly-iii` ([setup](../../docs/mcp/firefly-iii.md)) | ✅ yes (official image is amd64-only) |
| Linkding ([#15](https://github.com/prineycom/svc-personal-dashboard/issues/15)) | — | ❌ native HTTP image |

## How to add a bridged MCP

Add a service to the root `docker-compose.yml`:

```yaml
    build:
      context: ./services/_mcp
      args:
    restart: unless-stopped
    depends_on:
        condition: service_healthy
    environment:
    expose:
      - "8000"
    ports:
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

port `8000` **in the Dokploy UI** (do not add Traefik labels to compose). The
streamable-HTTP endpoint defaults to `/mcp`, so Hermes connects to

The exact env-var names depend on the wrapped package — check its README and
map them onto the `<SERVICE>_MCP_*` keys in the root `.env`.


(pinned `@0.2.0`). The bridge image installs the package at build time and runs
it offline via `npx --no-install`, so a cold start never contacts the npm
registry.

### Environment variables

The container reads these (names are fixed by the package):

| Variable            | Required | Set where                | Value / format                                                                 |
|---------------------|----------|--------------------------|--------------------------------------------------------------------------------|
| `LOG_LEVEL`         | no       | compose (optional)       | `debug` \| `info` (default) \| `warn` \| `error`.                              |
| `DEBUG`             | no       | compose (optional)       | Set to `true` for verbose diagnostics.                                         |

The token is auto-detected (`tk_` → API token, `eyJ` → JWT); no auth-type flag
is needed.

### Step-by-step

   Create token**. Grant at least Tasks, Projects, and Labels (read + write).
   Copy the `tk_…` value.
2. **Put it in the root `.env`:**
   ```dotenv
   ```
   Never commit `.env` (it is git-ignored); the token lives only there / in
   Dokploy → Environment.
   → container port `8000`, entrypoint `web`. No `traefik.*` labels in compose.
5. **Register in Hermes:** point Hermes at

### Verify

```bash
# Health (supergateway is up):

  "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{},\"clientInfo\":{\"name\":\"v\",\"version\":\"1\"}}}" \
  "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}" \
#   filters/templates/webhooks/batch_import/auth
```

