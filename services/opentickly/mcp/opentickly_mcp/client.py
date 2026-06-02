"""Async HTTP client wrapping the OpenTickly (Toggl-compatible) API.

Covers the Track API v9 endpoints the tools need plus the Reports API v3 search
endpoint. Authentication is Toggl-style HTTP Basic: username = API token,
password = the literal string ``api_token``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from .config import Config

CREATED_WITH = "opentickly-mcp"


class TogglError(RuntimeError):
    """Upstream OpenTickly call failed (transport error or non-2xx status)."""


class TogglClient:
    def __init__(self, config: Config, client: httpx.AsyncClient | None = None) -> None:
        self._config = config
        self._client = client or httpx.AsyncClient(
            base_url=config.base_url,
            auth=(config.api_token, "api_token"),
            timeout=httpx.Timeout(30.0),
            headers={"Content-Type": "application/json"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        try:
            response = await self._client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise TogglError(f"OpenTickly request failed: {exc}") from exc
        if response.status_code >= 400:
            raise TogglError(
                f"OpenTickly {method} {url} -> {response.status_code}: {response.text}"
            )
        if response.content:
            return response.json()
        return None

    async def me(self) -> dict[str, Any]:
        return await self._request("GET", "/api/v9/me")

    async def resolve_workspace_id(self) -> int:
        if self._config.workspace_id is not None:
            return self._config.workspace_id
        me = await self.me()
        workspace_id = me.get("default_workspace_id")
        if not workspace_id:
            raise TogglError("no default_workspace_id from /api/v9/me; set OPENTICKLY_WORKSPACE_ID")
        return int(workspace_id)

    async def start_time_entry(
        self,
        description: str,
        workspace_id: int,
        project_id: int | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "description": description,
            "workspace_id": workspace_id,
            "start": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "duration": -1,
            "created_with": CREATED_WITH,
        }
        if project_id is not None:
            body["project_id"] = project_id
        if tags:
            body["tags"] = tags
        return await self._request(
            "POST", f"/api/v9/workspaces/{workspace_id}/time_entries", json=body
        )

    async def stop_time_entry(self, workspace_id: int, time_entry_id: int) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/api/v9/workspaces/{workspace_id}/time_entries/{time_entry_id}/stop",
        )

    async def current_time_entry(self) -> dict[str, Any] | None:
        return await self._request("GET", "/api/v9/me/time_entries/current")

    async def list_time_entries(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        result = await self._request("GET", "/api/v9/me/time_entries", params=params or None)
        return result or []

    async def search_time_entries(
        self, workspace_id: int, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        body = {"start_date": start_date, "end_date": end_date}
        result = await self._request(
            "POST",
            f"/reports/api/v3/workspace/{workspace_id}/search/time_entries",
            json=body,
        )
        return result or []
