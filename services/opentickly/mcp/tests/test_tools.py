"""Smoke tests: request building, response parsing and tool error handling.

All HTTP is mocked with respx — no network. asyncio_mode=auto (pyproject) runs
the async tests without explicit markers.
"""

from __future__ import annotations

import json

import httpx
import respx

from opentickly_mcp import server
from opentickly_mcp.client import TogglClient
from opentickly_mcp.config import Config

BASE = "http://opentickly:8080"


def make_client() -> TogglClient:
    return TogglClient(Config(base_url=BASE, api_token="tok", workspace_id=123))


@respx.mock
async def test_start_time_entry_builds_request() -> None:
    route = respx.post(f"{BASE}/api/v9/workspaces/123/time_entries").mock(
        return_value=httpx.Response(200, json={"id": 1, "description": "work", "duration": -1})
    )
    client = make_client()
    result = await client.start_time_entry(description="work", workspace_id=123)

    assert route.called
    body = json.loads(route.calls.last.request.content)
    assert body["description"] == "work"
    assert body["duration"] == -1
    assert body["created_with"] == "opentickly-mcp"
    assert result["id"] == 1
    await client.aclose()


@respx.mock
async def test_stop_time_entry_patches_stop_endpoint() -> None:
    route = respx.patch(f"{BASE}/api/v9/workspaces/123/time_entries/55/stop").mock(
        return_value=httpx.Response(200, json={"id": 55, "duration": 600})
    )
    client = make_client()
    result = await client.stop_time_entry(workspace_id=123, time_entry_id=55)

    assert route.called
    assert result["id"] == 55
    await client.aclose()


@respx.mock
async def test_list_time_entries_passes_dates_and_handles_empty() -> None:
    route = respx.get(f"{BASE}/api/v9/me/time_entries").mock(
        return_value=httpx.Response(200, json=[])
    )
    client = make_client()
    result = await client.list_time_entries(start_date="2026-06-01", end_date="2026-06-02")

    assert route.called
    assert dict(route.calls.last.request.url.params) == {
        "start_date": "2026-06-01",
        "end_date": "2026-06-02",
    }
    assert result == []
    await client.aclose()


@respx.mock
async def test_search_time_entries_uses_reports_v3() -> None:
    route = respx.post(f"{BASE}/reports/api/v3/workspace/123/search/time_entries").mock(
        return_value=httpx.Response(200, json=[{"description": "work", "seconds": 600}])
    )
    client = make_client()
    result = await client.search_time_entries(
        workspace_id=123, start_date="2026-06-01", end_date="2026-06-02"
    )

    assert route.called
    assert result[0]["seconds"] == 600
    await client.aclose()


@respx.mock
async def test_resolve_workspace_id_falls_back_to_me() -> None:
    respx.get(f"{BASE}/api/v9/me").mock(
        return_value=httpx.Response(200, json={"default_workspace_id": 777})
    )
    client = TogglClient(Config(base_url=BASE, api_token="tok"))
    assert await client.resolve_workspace_id() == 777
    await client.aclose()


@respx.mock
async def test_stop_timer_tool_reports_no_running_timer() -> None:
    respx.get(f"{BASE}/api/v9/me/time_entries/current").mock(
        return_value=httpx.Response(200, json=None)
    )
    server._client = make_client()
    result = await server.stop_timer.fn()
    assert result == {"message": "no running timer to stop"}
    server._client = None


@respx.mock
async def test_get_report_tool_wraps_upstream_error() -> None:
    respx.post(f"{BASE}/reports/api/v3/workspace/123/search/time_entries").mock(
        return_value=httpx.Response(500, text="boom")
    )
    server._client = make_client()
    result = await server.get_report.fn(start_date="2026-06-01", end_date="2026-06-02")
    assert "error" in result
    assert "500" in result["error"]
    server._client = None
