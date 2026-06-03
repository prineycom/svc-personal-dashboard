"""FastMCP server exposing the BeaverHabits habit tracker over streamable-HTTP.

Registers four habit tools backed by the BeaverHabits REST API plus a
dependency-free ``/healthz`` route used by the container healthcheck. All
HTTP/auth concerns live in :mod:`client`; this module only wires tools.

Run directly to serve the MCP at ``/mcp`` on ``0.0.0.0:8000``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date as date_cls
from typing import Any

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from client import BeaverHabitsClient

DATE_FMT = "%d-%m-%Y"

_client = BeaverHabitsClient()


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[None]:
    """Close the shared client's HTTP pool when the server shuts down."""
    try:
        yield
    finally:
        await _client.aclose()


mcp: FastMCP = FastMCP(name="beaverhabits", lifespan=lifespan)


async def _list_habits() -> list[dict[str, Any]]:
    """Fetch the raw habit list from the BeaverHabits API."""
    response = await _client.request("GET", "/api/v1/habits")
    data = response.json()
    return data if isinstance(data, list) else []


@mcp.tool
async def list_habits() -> list[dict[str, Any]]:
    """List all habits in the BeaverHabits account.

    Returns each habit's ``id`` and ``name`` so the caller can reference a
    habit in the other tools.
    """
    habits = await _list_habits()
    return [
        {"id": habit.get("id"), "name": habit.get("name")}
        for habit in habits
    ]


@mcp.tool
async def get_habit(habit_id: str) -> dict[str, Any]:
    """Get a single habit by its id.

    BeaverHabits has no single-habit GET endpoint, so this fetches the full
    habit list and filters for the matching ``habit_id``. Returns the habit's
    ``id`` and ``name``, or ``{"found": false, ...}`` when no habit matches.
    """
    for habit in await _list_habits():
        if str(habit.get("id")) == str(habit_id):
            return {"id": habit.get("id"), "name": habit.get("name")}
    return {"found": False, "habit_id": habit_id, "error": "Habit not found."}


@mcp.tool
async def complete_habit(
    habit_id: str,
    date: str | None = None,
    done: bool = True,
) -> dict[str, Any]:
    """Mark a habit complete (or incomplete) for a given day.

    ``date`` is a ``DD-MM-YYYY`` string and defaults to today. Set ``done`` to
    ``False`` to clear a completion. Returns the API's ``{day, done}`` result.
    """
    if date is None:
        date = date_cls.today().strftime(DATE_FMT)
    response = await _client.request(
        "POST",
        f"/api/v1/habits/{habit_id}/completions",
        json={"date_fmt": DATE_FMT, "date": date, "done": done},
    )
    return response.json()


@mcp.tool
async def get_completions(
    habit_id: str,
    date_start: str,
    date_end: str,
    sort: str = "asc",
) -> Any:
    """List the days a habit was completed within a date range.

    ``date_start`` and ``date_end`` are inclusive ``DD-MM-YYYY`` strings;
    ``sort`` is ``"asc"`` or ``"desc"``. Returns the completed date strings.
    """
    response = await _client.request(
        "GET",
        f"/api/v1/habits/{habit_id}/completions",
        params={
            "date_fmt": DATE_FMT,
            "date_start": date_start,
            "date_end": date_end,
            "sort": sort,
        },
    )
    return response.json()


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> PlainTextResponse:
    """Liveness probe that returns HTTP 200 without calling BeaverHabits."""
    return PlainTextResponse("ok")


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
