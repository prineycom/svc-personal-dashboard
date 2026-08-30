# ─────────────────────────────────────────────────────────────────────────────
# BeaverHabits MCP server image.
#
# Native FastMCP server (streamable-HTTP) — no supergateway bridge needed.
# Exposes the habit tools at /mcp with a /healthz liveness route.
#
# Conventions (see docs/mcp/CONVENTIONS.md):
#   • Pin the base image — never :latest.
#   • Listen on port 8000, health at /healthz.
#   • Service URL and auth token come from env injected via compose.
#
# fastmcp + httpx are pure-Python / manylinux wheels, so slim needs no build
# tooling.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install pinned deps first so the layer caches across source-only changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# server.py imports client as a sibling module — both must share the workdir.
COPY client.py server.py ./

EXPOSE 8000

CMD ["python", "server.py"]
