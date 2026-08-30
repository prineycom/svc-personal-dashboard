"""Async HTTP client for the BeaverHabits REST API.

Encapsulates transport and OAuth2-password-grant authentication so the FastMCP
tool layer (``server.py``) stays free of auth/HTTP concerns. Configuration is
read from the environment:

- ``BEAVERHABITS_MCP_URL``      internal upstream base URL
                               (default ``http://beaverhabits:8080``)
- ``BEAVERHABITS_MCP_EMAIL``    account email (OAuth2 ``username``)
- ``BEAVERHABITS_MCP_PASSWORD`` account password
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://beaverhabits:8080"


class BeaverHabitsAuthError(RuntimeError):
    """Raised when authentication against BeaverHabits fails.

    Surfaced (instead of returning empty data) so a misconfiguration such as
    wrong credentials produces a clear error rather than a silent empty result.
    """


class BeaverHabitsClient:
    """Thin async wrapper around the BeaverHabits ``/api/v1`` REST API.

    Performs a lazy OAuth2 password-grant login on first use, caches the bearer
    token, and transparently re-logs-in once when a request returns ``401``.
    """

    def __init__(
        self,
        base_url: str | None = None,
        email: str | None = None,
        password: str | None = None,
    ) -> None:
        self._base_url = (
            base_url
            if base_url is not None
            else os.environ.get("BEAVERHABITS_MCP_URL", DEFAULT_BASE_URL)
        ).rstrip("/")
        self._email = (
            email if email is not None else os.environ.get("BEAVERHABITS_MCP_EMAIL", "")
        )
        self._password = (
            password
            if password is not None
            else os.environ.get("BEAVERHABITS_MCP_PASSWORD", "")
        )
        self._token: str | None = None
        self._lock = asyncio.Lock()
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)

    async def login(self) -> str:
        """Authenticate via OAuth2 password grant and cache the bearer token.

        POSTs form-encoded ``grant_type=password`` credentials to
        ``/auth/login`` and stores the returned ``access_token``. Raises
        :class:`BeaverHabitsAuthError` on failure (e.g. bad credentials).
        """
        if not self._email or not self._password:
            raise BeaverHabitsAuthError(
                "BeaverHabits credentials are not configured: set "
                "BEAVERHABITS_MCP_EMAIL and BEAVERHABITS_MCP_PASSWORD."
            )

        response = await self._client.post(
            "/auth/login",
            data={
                "grant_type": "password",
                "username": self._email,
                "password": self._password,
            },
        )
        if response.status_code != httpx.codes.OK:
            raise BeaverHabitsAuthError(
                f"BeaverHabits login failed with HTTP {response.status_code}: "
                f"{response.text}"
            )

        try:
            payload = response.json()
        except ValueError as exc:  # noqa: PERF203 - clarity over micro-perf
            raise BeaverHabitsAuthError(
                "BeaverHabits login returned a non-JSON response."
            ) from exc

        token = payload.get("access_token")
        if not token:
            raise BeaverHabitsAuthError(
                "BeaverHabits login response did not include an access_token."
            )

        self._token = token
        return token

    async def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Issue an authenticated request, re-logging-in once on ``401``.

        Injects ``Authorization: Bearer <token>`` (logging in first if no token
        is cached). If the response is ``401`` the token is discarded, a fresh
        login is performed, and the request is retried exactly once.

        Token refresh is guarded by an :class:`asyncio.Lock` with
        double-checked locking so that concurrent in-flight requests share a
        single ``/auth/login`` instead of each firing a redundant one.
        """
        if self._token is None:
            await self._refresh_token(None)

        token = self._token
        response = await self._send(method, path, **kwargs)
        if response.status_code == httpx.codes.UNAUTHORIZED:
            await self._refresh_token(token)
            response = await self._send(method, path, **kwargs)

        response.raise_for_status()
        return response

    async def _refresh_token(self, stale_token: str | None) -> None:
        """Log in once even under concurrent callers (double-checked locking).

        ``stale_token`` is the token value the caller already tried (or
        ``None`` for the initial login). The lock is acquired and the cached
        token re-checked: a fresh login is only performed if another coroutine
        has not already replaced ``stale_token`` with a newer token.
        """
        async with self._lock:
            if self._token is None or self._token == stale_token:
                await self.login()

    async def _send(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        headers = dict(kwargs.pop("headers", {}) or {})
        headers["Authorization"] = f"Bearer {self._token}"
        return await self._client.request(method, path, headers=headers, **kwargs)

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._client.aclose()
