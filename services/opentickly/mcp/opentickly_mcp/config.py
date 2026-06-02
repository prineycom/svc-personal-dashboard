"""Runtime configuration read from the environment.

Kept free of import-time side effects: `Config.from_env()` is called lazily on
the first tool invocation, so importing the package without a token never fails.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_BASE_URL = "http://opentickly:8080"


@dataclass(frozen=True)
class Config:
    """Base URL, API token and optional workspace for the OpenTickly upstream."""

    base_url: str
    api_token: str
    workspace_id: int | None = None

    @classmethod
    def from_env(cls) -> Config:
        token = os.environ.get("TOGGL_API_TOKEN", "").strip()
        if not token:
            raise RuntimeError("TOGGL_API_TOKEN is required")
        base_url = os.environ.get("OPENTICKLY_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        raw_workspace = os.environ.get("OPENTICKLY_WORKSPACE_ID", "").strip()
        workspace_id = int(raw_workspace) if raw_workspace else None
        return cls(base_url=base_url, api_token=token, workspace_id=workspace_id)
