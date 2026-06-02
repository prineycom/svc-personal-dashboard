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
| Wger ([#14](https://github.com/prineycom/svc-personal-dashboard/issues/14)) | `Juxsta/wger-mcp` | ✅ yes |
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
      VIKUNJA_URL: http://vikunja:3456          # internal hostname, not public
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
