"""FastMCP server: native streamable-HTTP on :8000 (/mcp) with a /healthz route.

Tools are registered in this module. The Toggl client is built lazily on first
use so importing this module needs no environment configuration.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from .client import TogglClient, TogglError
from .config import Config

_client: TogglClient | None = None
_client_lock = asyncio.Lock()


async def get_client() -> TogglClient:
    """Return the shared Toggl client, building it from env on first call."""
    global _client
    if _client is None:
        async with _client_lock:
            if _client is None:
                _client = TogglClient(Config.from_env())
    return _client


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[None]:
    """Close the shared client on shutdown."""
    global _client
    try:
        yield
    finally:
        if _client is not None:
            await _client.aclose()
            _client = None


mcp = FastMCP("OpenTickly", lifespan=lifespan)


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


@mcp.tool
async def start_timer(
    description: str,
    project_id: int | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Start a running time entry in OpenTickly.

    `description` is the entry text. `project_id` and `tags` are optional. The
    workspace is taken from OPENTICKLY_WORKSPACE_ID or the user's default.
    """
    client = await get_client()
    try:
        workspace_id = await client.resolve_workspace_id()
        return await client.start_time_entry(
            description=description, workspace_id=workspace_id, project_id=project_id, tags=tags
        )
    except TogglError as exc:
        return {"error": str(exc)}


@mcp.tool
async def stop_timer(time_entry_id: int | None = None) -> dict[str, Any]:
    """Stop a running time entry.

    With no `time_entry_id`, stops the currently running entry. Returns a clear
    message when nothing is running.
    """
    client = await get_client()
    try:
        if time_entry_id is None:
            current = await client.current_time_entry()
            if not current:
                return {"message": "no running timer to stop"}
            time_entry_id = int(current["id"])
        workspace_id = await client.resolve_workspace_id()
        return await client.stop_time_entry(workspace_id=workspace_id, time_entry_id=time_entry_id)
    except TogglError as exc:
        return {"error": str(exc)}


@mcp.tool
async def list_time_entries(
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]] | dict[str, str]:
    """List the user's time entries, optionally bounded by `start_date`/`end_date`.

    Dates are ISO-8601 (`YYYY-MM-DD` or RFC3339). Returns the most recent entries
    when no range is given.
    """
    client = await get_client()
    try:
        return await client.list_time_entries(start_date=start_date, end_date=end_date)
    except TogglError as exc:
        return {"error": str(exc)}


@mcp.tool
async def get_report(start_date: str, end_date: str) -> list[dict[str, Any]] | dict[str, str]:
    """Fetch a time-entry report for a date range via the Reports API v3.

    `start_date` and `end_date` are ISO-8601 dates (`YYYY-MM-DD`). Returns an
    empty list when no entries fall in the range.
    """
    client = await get_client()
    try:
        workspace_id = await client.resolve_workspace_id()
        return await client.search_time_entries(
            workspace_id=workspace_id, start_date=start_date, end_date=end_date
        )
    except TogglError as exc:
        return {"error": str(exc)}


def main() -> None:
    mcp.run(transport="http", host="0.0.0.0", port=8000, path="/mcp")


if __name__ == "__main__":
    main()
