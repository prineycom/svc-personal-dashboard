# Native FastMCP image for OpenTickly. Streamable-HTTP on :8000 (/mcp),
# health at /healthz. Pin the base by digest — never :latest (see
# docs/mcp/CONVENTIONS.md). Tag kept for readability; digest is authoritative.
FROM python:3.12-slim@sha256:090ba77e2958f6af52a5341f788b50b032dd4ca28377d2893dcf1ecbdfdfe203

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
