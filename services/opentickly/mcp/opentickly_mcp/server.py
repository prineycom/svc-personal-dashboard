"""FastMCP server: native streamable-HTTP on :8000 (/mcp) with a /healthz route.

Tools are registered in this module. The Toggl client is built lazily on first
use so importing this module needs no environment configuration.
"""

from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from .client import TogglClient
from .config import Config

mcp = FastMCP("OpenTickly")

_client: TogglClient | None = None


def get_client() -> TogglClient:
    """Return the shared Toggl client, building it from env on first call."""
    global _client
    if _client is None:
        _client = TogglClient(Config.from_env())
    return _client


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def main() -> None:
    mcp.run(transport="http", host="0.0.0.0", port=8000, path="/mcp")


if __name__ == "__main__":
    main()
