# Native FastMCP image for OpenTickly. Streamable-HTTP on :8000 (/mcp),
# health at /healthz. Pin the base — never :latest (see docs/mcp/CONVENTIONS.md).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install runtime deps only (no dev extras).
COPY pyproject.toml ./
COPY opentickly_mcp ./opentickly_mcp
RUN pip install .

EXPOSE 8000

# Console script from pyproject [project.scripts]; runs opentickly_mcp.server:main.
CMD ["opentickly-mcp"]
