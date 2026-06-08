# ─────────────────────────────────────────────────────────────────────────────
# Reusable MCP bridge image.
#
# Wraps a stdio-only MCP server in a streamable-HTTP endpoint via supergateway,
# so Hermes can reach it over HTTP/SSE (through Traefik + Tailscale) like any
# other service in the Blueprint.
#
# Use for MCP servers that ship stdio-only and have no official Docker image
# (Vikunja), OR whose official image has no build for the target arch
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

# stdio -> streamable-HTTP. Use `npx --no-install` so npx resolves the package
# already installed globally above and NEVER contacts the npm registry at
# runtime — `npx -y` would hit registry.npmjs.org on every cold start and fail
# on the internal (egress-less) network with EAI_AGAIN. `${MCP_PKG%@*}` strips
# the trailing `@version` so npx matches the installed name.
# JSON exec form (sh -c) so the linter is happy and signals reach supergateway;
# sh is still needed to expand ${MCP_PKG} / ${MCP_PORT} at runtime.
#
# --stateful is REQUIRED: in the default stateless mode supergateway 3.4.0
# shares one stdio child across per-request transports, and when a child
# response arrives for a request whose HTTP connection already closed (client
# timeout / disconnect) it throws `No connection established for request ID: N`
# from inside the stdout socket handler — an UNCAUGHT exception that kills the
# whole process (exit 1). The container restart-loops, /healthz keeps lying
# "ok", and the connected agent (Hermes) loses its toolset until restarted.
# Stateful mode gives each MCP session its own transport + id mapping, so a
# late/orphaned response is never written to a stranger's closed connection.
# --sessionTimeout reaps sessions (and their child process) abandoned without an
# explicit terminate — otherwise they'd leak forever on the Pi across restarts.
CMD ["sh", "-c", "exec supergateway --stdio \"npx --no-install ${MCP_PKG%@*}\" --outputTransport streamableHttp --stateful --sessionTimeout 1800000 --port \"${MCP_PORT}\" --healthEndpoint /healthz"]
