# Code Review: 16-beaverhabits-fastmcp

## Summary

### Context and goal

Issue #16 adds the first concrete MCP service to the repo: a native Python + FastMCP server exposing BeaverHabits over streamable-HTTP at `/mcp`, calling the BeaverHabits REST API (`/api/v1`) over the internal Docker network. It ships four tools (`list_habits`, `get_habit`, `complete_habit`, `get_completions`), a `/healthz` route, a Dockerfile, a `docker-compose.yml` service block, and `.env.example` keys. Auth is OAuth2 password grant (no static token).

### Key code areas for review

1. **`services/beaverhabits/mcp/client.py:login()`** — form-encoded `/auth/login`, caches `access_token`, raises `BeaverHabitsAuthError` on failure.
2. **`services/beaverhabits/mcp/client.py:request()` + `_refresh_token()`** — bearer injection, lock-guarded double-checked re-login, exactly-once 401 retry.
3. **`services/beaverhabits/mcp/server.py` tools** — the four habit tools; `get_habit` filters the list (DD-4).
4. **`services/beaverhabits/mcp/server.py:lifespan`** — closes the httpx pool on shutdown.
5. **`docker-compose.yml` `mcp-beaverhabits` block** — native convention, Python-probe healthcheck, no Traefik labels.
6. **`services/beaverhabits/mcp/Dockerfile`** — `python:3.12-slim`, pinned deps.

### Complex decisions

1. **Lazy login + cached token + once-only 401 re-login** (`client.py`) — minimizes logins; now lock-guarded against concurrent refresh.
2. **`get_habit` derived from `list_habits`** (`server.py`) — no single-habit GET exists in the BeaverHabits API (DD-4).
3. **Python urllib healthcheck instead of wget** (`docker-compose.yml`) — `python:3.12-slim` ships no `wget`/`curl`; the Python probe needs no extra image layer.

### Questions for the reviewer

1. Should the upstream wait on `condition: service_healthy` for `beaverhabits` rather than `service_started`? Current choice tolerates BeaverHabits still warming up (the MCP only logs in on first tool call, not at boot).
2. Is a single shared client instance acceptable long-term, or should per-call clients be considered if Hermes drives high concurrency?

### Risks and impact

- Token refresh and pool lifecycle are now synchronized and closed; residual risk is low.
- Healthcheck verified: container reports **healthy** in ~3 s; previously it would have been perma-`unhealthy` (no `wget` in image).
- No automated tests (consistent with this infra repo).

### Tests and manual checks

**Auto-tests:** none (infra repo, no test harness). Optional follow-up: unit tests for `client.request` 401-refresh with a mocked transport.

**Manual scenarios:**
1. `docker compose build mcp-beaverhabits` → image builds.
2. `BEAVERHABITS_MCP_PORT=8090 docker compose up -d mcp-beaverhabits` → container reaches `healthy`; `wget -qO- http://localhost:8090/healthz` → `ok`.
3. With real creds, call `list_habits` / `complete_habit` / `get_completions` from an MCP client → live data round-trip.

### Out of scope

- Dokploy subdomain registration and Hermes endpoint registration (documented as manual in the service README).
- The existing `beaverhabits` service block; the `_mcp` supergateway bridge.

## Commits

| Hash      | Description                                                          |
| --------- | ------------------------------------------------------------------- |
| `67beed6` | docs(16-beaverhabits-fastmcp): add MCP service README               |
| `9db0602` | feat(16-beaverhabits-fastmcp): add FastMCP server and BeaverHabits client |
| `845bc4a` | chore(16-beaverhabits-fastmcp): add MCP server Dockerfile           |
| `602db92` | feat(16-beaverhabits-fastmcp): wire mcp-beaverhabits compose service and env keys |
| `4ebec22` | docs(16-beaverhabits-fastmcp): add execution report                 |
| `099ae44` | fix(16-beaverhabits-fastmcp): fix 3 review issues                   |

## Changed Files

| File                                       | +/-   | Description                                          |
| ------------------------------------------ | ----- | ---------------------------------------------------- |
| services/beaverhabits/mcp/client.py        | +157  | Async httpx client; OAuth2 login, lock-guarded refresh |
| services/beaverhabits/mcp/server.py        | +128  | FastMCP tools + `/healthz` + lifespan pool close      |
| services/beaverhabits/mcp/Dockerfile       | +28   | `python:3.12-slim`, pinned deps, runs server on 8000  |
| services/beaverhabits/mcp/README.md        | +64   | Native FastMCP doc + manual Dokploy/Hermes/verify     |
| services/beaverhabits/mcp/requirements.txt | +2    | Pinned `fastmcp==2.14.7`, `httpx==0.28.1`            |
| docker-compose.yml                         | +31   | Native `mcp-beaverhabits` service, Python-probe healthcheck |
| .env.example                               | +5    | `BEAVERHABITS_MCP_EMAIL/PASSWORD/URL` + `TOKEN`-unused note |

## Issues Found

| Severity  | Score | Category      | File:line                          | Description                                                                 |
| --------- | ----- | ------------- | ---------------------------------- | --------------------------------------------------------------------------- |
| Important | 72    | bug           | docker-compose.yml healthcheck     | `python:3.12-slim` has no `wget`/`curl` → healthcheck unresolvable, container perma-`unhealthy` |
| Minor     | 44    | reliability   | client.py token refresh            | No lock around cached token → concurrent 401s cause redundant re-logins      |
| Minor     | 40    | resource-leak | client.py `aclose` / server.py     | `aclose()` defined but never wired into FastMCP lifespan → httpx pool leaks  |
| Minor     | 30    | robustness    | client.py login error             | Login failure surfaces upstream `response.text` unbounded into errors/logs  |
| Minor     | 22    | consistency   | README.md:62                       | Local-test snippet may imply in-container `wget` works (tied to healthcheck) |

## Fixed Issues

| Issue                                   | Commit    | Description                                                          |
| --------------------------------------- | --------- | ------------------------------------------------------------------- |
| Healthcheck binary missing (Important)  | `099ae44` | Replaced wget healthcheck with a dependency-free Python urllib probe; container now reaches `healthy` |
| Token refresh race (Minor)              | `099ae44` | Added `asyncio.Lock` + double-checked `_refresh_token(stale_token)`  |
| httpx pool leak (Minor)                 | `099ae44` | Wired `aclose()` into a FastMCP `lifespan` context manager           |

## Skipped Issues

| Issue                                        | Reason                                                                 |
| -------------------------------------------- | --------------------------------------------------------------------- |
| client.py login error text unbounded (Minor) | Excluded by user (low risk — BeaverHabits login error body does not echo the password; password is never interpolated into errors/logs) |
| README in-container wget note (Minor)        | Excluded by user (cosmetic; host-side `wget` in the snippet is valid)  |

## Recommendations

- For the two skipped minors: when convenient, truncate the upstream body in `BeaverHabitsAuthError` and re-confirm the README's local-test snippet matches the Python-probe healthcheck.
- Consider whether `depends_on` should use `condition: service_healthy` for `beaverhabits` (the BeaverHabits container has no healthcheck today, so this would need one added first).
- Optional: add unit tests for the 401-refresh path in `client.request` with a mocked httpx transport, the one piece not covered by the docker smoke test.
