# ─────────────────────────────────────────────────────────────────────────────
# Reusable MCP bridge image.
#
# Wraps a stdio-only MCP server in a streamable-HTTP endpoint via supergateway,
# so Hermes can reach it over HTTP/SSE (through Traefik + Tailscale) like any
# other service in the Blueprint.
#
# Use for MCP servers that ship stdio-only and have no official Docker image
# (Vikunja, Wger), OR whose official image has no build for the target arch
# (Firefly III: image is amd64-only, npm package is multi-arch — bridge it on
# the Pi). MCP servers with a native-HTTP image for the target arch (Linkding)
# run their own image directly — no bridge.
#
# Conventions (see docs/mcp/CONVENTIONS.md):
#   • Pin both supergateway AND the wrapped package — never :latest.
#   • Listen on port 8000, health at /healthz.
#   • The wrapped server reads its own config (service URL, token) from env
#     injected via compose — see the per-service environment: block.
#
# Build per service via compose `build.args`:
#   build:
#     context: ./services/_mcp
#     args:
#       MCP_PKG: "@democratize-technology/vikunja-mcp@0.2.0"
# ─────────────────────────────────────────────────────────────────────────────
FROM node:22-alpine

# Pin the bridge. Bump deliberately.
ARG SUPERGATEWAY_VERSION=3.4.0

# The stdio MCP npm package WITH a pinned version,
# e.g. @democratize-technology/vikunja-mcp@0.2.0
ARG MCP_PKG

# Carry MCP_PKG into the runtime layer (ARG is build-time only; CMD needs ENV).
ENV MCP_PKG=${MCP_PKG}
ENV MCP_PORT=8000

# Install both the bridge and the wrapped server at build time so startup needs
# no network (more reliable on the Pi than a runtime `npx` download).
RUN npm install -g "supergateway@${SUPERGATEWAY_VERSION}" "${MCP_PKG}"

EXPOSE 8000

# stdio -> streamable-HTTP. `npx -y` resolves the already-installed global pkg.
# JSON exec form (sh -c) so the linter is happy and signals reach supergateway;
# sh is still needed to expand ${MCP_PKG} / ${MCP_PORT} at runtime.
CMD ["sh", "-c", "exec supergateway --stdio \"npx -y ${MCP_PKG}\" --outputTransport streamableHttp --port \"${MCP_PORT}\" --healthEndpoint /healthz"]
