# BeaverHabits FastMCP server

**Slug:** 16-beaverhabits-fastmcp
**Ticket:** https://github.com/prineycom/svc-personal-dashboard/issues/16
**Complexity:** medium
**Type:** general

## Task

Build a native Python + FastMCP server that exposes BeaverHabits over streamable-HTTP and ships as a container in the root `docker-compose.yml`.

## Context

### Area architecture

BeaverHabits runs as service `beaverhabits` (`docker-compose.yml:454`, image `daya0576/beaverhabits:0.9.1`, listens on `8080`). It exposes a REST API under `/api/v1` and authenticates via OAuth2 password grant — `POST /auth/login` with `username`+`password` returns `{access_token, token_type: bearer}`; every API call then carries `Authorization: Bearer <token>`. There is no static API-token feature.

Stage 2 connects each service to the Hermes AI agent through a per-service MCP container. ADR 0007 (`docs/adr/0007-mcp-integration-topology.md`) fixes the topology: remote MCP over HTTP/SSE, one container per direction, behind a Traefik subdomain (`mcp-<svc>.dashboard.example.com`) managed in the Dokploy UI, protected by Tailscale. BeaverHabits is designated a **native FastMCP** server (own Python image, no supergateway bridge) — `docs/mcp/CONVENTIONS.md:25`, ADR 0007 line 41.

This is the **first concrete MCP service** in the repo: `#10` laid down the conventions, the `_mcp` bridge image, ADR 0007, and `.env` placeholders, but `docker-compose.yml` contains no MCP service block yet.

Data flow: Hermes → (Tailscale + Traefik) → `mcp-beaverhabits` container `/mcp` → BeaverHabits REST API at `http://beaverhabits:8080/api/v1` over the `internal` network.

### Files to change

- `services/beaverhabits/mcp/` — new directory (per convention `services/<svc>/mcp/` for own FastMCP, `docs/mcp/CONVENTIONS.md:31`). Currently `services/beaverhabits/` is empty. Add:
  - FastMCP server source (the four tools + a `/healthz` route).
  - `Dockerfile` (lightweight Python, pinned base tag, pinned FastMCP version).
  - dependency manifest (e.g. `requirements.txt` or `pyproject.toml`).
  - `README.md` documenting the manual Dokploy/Hermes/verify steps.
- `docker-compose.yml` — add the `mcp-beaverhabits` service block (insert near the other MCP/service blocks). Model it on the native Firefly III snippet at `docs/mcp/CONVENTIONS.md:80`.
- `.env.example:102` (BeaverHabits section) and `.env.example:119` — add `BEAVERHABITS_MCP_EMAIL`, `BEAVERHABITS_MCP_PASSWORD`, and `BEAVERHABITS_MCP_URL` (internal upstream). `BEAVERHABITS_MCP_TOKEN` (`.env.example:119`) is unused for this service — document why in a comment.

### Patterns to reuse

- **Native MCP compose block** — `docs/mcp/CONVENTIONS.md:80-108` (Firefly III): `restart: unless-stopped`, `depends_on: beaverhabits`, `environment:` mapping `.env` keys to image env, `expose: ["8000"]`, `ports: ["${BEAVERHABITS_MCP_PORT:-}:8000"]`, `healthcheck` via `wget` against the health path, `deploy.resources.limits.memory: 128M`, `networks: [internal, dokploy-network]`.
- **Internal upstream URL** — `http://beaverhabits:8080` (`docs/mcp/CONVENTIONS.md:55`); MCP must call the service over `internal`, never the public URL.
- **Secret namespacing** — service creds live in root `.env` under the `BEAVERHABITS_MCP_*` namespace, injected via the compose `environment:` block (`docs/mcp/CONVENTIONS.md:59`, `.env.example:108-128`).
- **Image pinning + memory limit + healthcheck shape** — `beaverhabits` service block (`docker-compose.yml:454`) and the `_mcp` Dockerfile (`services/_mcp/Dockerfile`) both pin tags and set limits; mirror that discipline.
- **README structure** — `services/_mcp/README.md` shows the "Who uses it / How to add / manual subdomain registration" layout to follow.

### Tests

No test suite exists in this repo (no `tests/`, no CI test config) — it is infrastructure + docs. Verification is by `docker compose config`, container build, and a live tool call (see Verification). If the implementer adds Python unit tests for the API client, keep them inside `services/beaverhabits/mcp/` and runnable without a live BeaverHabits instance (mock the HTTP layer).

## Requirements

1. Implement a FastMCP server exposing four tools over native streamable-HTTP on port `8000`:
   - `list_habits` → `GET /api/v1/habits`, returns habit `id`+`name` list.
   - `get_habit(habit_id)` → return the matching habit by filtering `list_habits` (no single-habit GET endpoint exists in the BeaverHabits API).
   - `complete_habit(habit_id, date, done)` → `POST /api/v1/habits/{habit_id}/completions` with body `{date_fmt, date, done}`; default `date` to today and `done` to `true`.
   - `get_completions(habit_id, date_start, date_end)` → `GET /api/v1/habits/{habit_id}/completions` with `date_fmt`, `date_start`, `date_end`, `sort`.
2. Authenticate by OAuth2 password grant: read `BEAVERHABITS_MCP_EMAIL` and `BEAVERHABITS_MCP_PASSWORD` from env, call `POST /auth/login` to obtain a bearer token, cache it, and re-login on expiry (401). Read the upstream base URL from `BEAVERHABITS_MCP_URL` (default `http://beaverhabits:8080`).
3. Expose a custom `/healthz` HTTP route on the FastMCP app that returns HTTP 200 without calling BeaverHabits.
4. Add a `Dockerfile` under `services/beaverhabits/mcp/` building a lightweight Python image with a pinned base tag and a pinned FastMCP version; the container listens on `8000` and serves streamable-HTTP at `/mcp`.
5. Add the `mcp-beaverhabits` service to `docker-compose.yml` following the native convention: `depends_on: beaverhabits`, `expose: ["8000"]`, `ports: ["${BEAVERHABITS_MCP_PORT:-}:8000"]`, `restart: unless-stopped`, `memory: 128M`, `networks: [internal, dokploy-network]`, healthcheck wgetting `http://localhost:8000/healthz`, and **no Traefik labels**.
6. Add `BEAVERHABITS_MCP_EMAIL`, `BEAVERHABITS_MCP_PASSWORD`, and `BEAVERHABITS_MCP_URL` to `.env.example`, and add a comment at `BEAVERHABITS_MCP_TOKEN` noting it is unused because BeaverHabits has no static token.
7. Add `services/beaverhabits/mcp/README.md` documenting the manual operational steps: register the `mcp-beaverhabits.dashboard.example.com` subdomain → port `8000` in the Dokploy UI, register `https://mcp-beaverhabits.dashboard.example.com/mcp` in Hermes, and the verify step (complete a habit from Hermes).

## Constraints

- Do not add Traefik labels to the compose block — routing is configured in the Dokploy UI for every service (`docs/mcp/CONVENTIONS.md:38`).
- Do not add a permanent `ports:` mapping beyond the `${BEAVERHABITS_MCP_PORT:-}:8000` local-test escape hatch (empty on Dokploy).
- Do not call BeaverHabits over its public URL — use the `internal` hostname `http://beaverhabits:8080`.
- Do not modify the existing `beaverhabits` service block (`docker-compose.yml:454`) or its volume/`user: "0:0"` workaround.
- Do not use the `services/_mcp/` supergateway bridge — BeaverHabits is native FastMCP, own image (ADR 0007 line 41).
- Do not pin any image, base, or package to `:latest` — pin every tag and version (`services/_mcp/Dockerfile:12`).
- Do not store credentials in git — they live only in the root `.env` (gitignored); `.env.example` carries empty placeholders only.
- Do not attempt to automate Dokploy subdomain or Hermes registration — document them as manual steps.

## Verification

- `docker compose config` → succeeds, shows `mcp-beaverhabits` on networks `internal` + `dokploy-network`, `expose: 8000`, no Traefik labels, `memory: 128M`.
- `docker compose build mcp-beaverhabits` → image builds with the pinned Python base and pinned FastMCP version.
- `BEAVERHABITS_MCP_PORT=8090 docker compose up -d mcp-beaverhabits` then `wget -qO- http://localhost:8090/healthz` → HTTP 200.
- With valid `BEAVERHABITS_MCP_EMAIL`/`BEAVERHABITS_MCP_PASSWORD`, an MCP client (or curl against `/mcp`) lists the four tools; `list_habits` returns the account's habits; `complete_habit` against a known habit id returns `{day, done: true}`; `get_completions` then includes that date.
- Edge case: an expired/invalid cached token triggers a transparent re-login (a second call after token expiry still succeeds), and a wrong-credentials login surfaces a clear error rather than a silent empty result.
- Edge case: `get_habit` with an unknown `habit_id` returns a not-found result, not a crash.
- `grep -n BEAVERHABITS_MCP .env.example` → shows `EMAIL`, `PASSWORD`, `URL`, and the `TOKEN` "unused" comment.

## Materials

- [Issue #16 — [beaverhabits] Свой FastMCP](https://github.com/prineycom/svc-personal-dashboard/issues/16)
- [BeaverHabits API How-to Guide](https://github.com/daya0576/beaverhabits/wiki/Beaver-Habit-Tracker-API-How%E2%80%90to-Guide)
- `docs/mcp/CONVENTIONS.md` — MCP layer conventions (native vs bridge, placement, routing, secrets, compose snippets)
- `docs/adr/0007-mcp-integration-topology.md` — MCP integration topology decision
- `services/_mcp/README.md`, `services/_mcp/Dockerfile` — bridge reference (not used here, but shows pinning/healthcheck discipline)
- `docker-compose.yml:454` — existing `beaverhabits` service block
- `.env.example:102-128` — BeaverHabits + MCP-layer env placeholders
- Epic: #9 · Depends on: #10
