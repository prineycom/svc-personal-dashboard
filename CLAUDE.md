# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This is a **template** (GitHub "template repository"), not a running service. It is
stamped into `svc-<name>` repos that each describe **one service's deployment** as
Docker Compose, deployed from git by [Dokploy](https://dokploy.com). There is no
application source here — only the deployment blueprint (`docker-compose.yml`,
optional `Dockerfile` + `config/`, `.env.example`). When working in a stamped
`svc-*` repo, the job is to fill in the `TODO`s, not to write app code.

## Architecture: the two-layer model

The single most important concept. Everything else follows from it.

- **Layer 1 — the blueprint (this repo / every `svc-*`):** machine-agnostic. It
  describes *what the service is* — image, container port, which env vars it
  consumes, resource caps, networks. It must contain **nothing** tied to a
  specific machine or deployment.
- **Layer 2 — per-machine wiring (Dokploy only, never git):** *where and how* it
  runs — the actual domain, secret values, tuned limits. Lives in each machine's
  Dokploy UI.

The seam between the layers is `${VAR}` references in `docker-compose.yml` whose
values are supplied by Dokploy → Environment. `.env.example` documents the *names*
crossing that seam; real values never enter git.

## Hard conventions (these are constraints, not preferences)

- **HTTP via Traefik only — no `ports:` for it.** Dokploy publishes container
  ports straight past the host firewall, so any `ports:` mapping becomes
  internet-facing. Expose an HTTP service with **Traefik labels** (see
  `docker-compose.yml`) whose host is `${SERVICE_DOMAIN}`. Use **one** routing
  method per service — these labels **or** Dokploy's Domains tab (which guesses
  the port, usually 3000), never both, or you get duplicate routers. A stray
  `ports:` on an HTTP service silently opens the box.
- **Raw TCP (a database) is the one allowed `ports:` exception.** Traefik proxies
  HTTP only, so a service like Postgres that external clients must reach has no
  Traefik route — publish a **parameterised** host port (`${DB_PUBLIC_PORT}:5432`)
  instead. That port *is* internet-facing (Docker DNAT bypasses the firewall), so
  it is only acceptable with a **strong password + a host-side fail2ban jail**.
  Keep it private (no `ports:`) unless an outside client genuinely needs it.
- **Pin image tags** — never `:latest`. Reproducible across machines and over time.
- **Nothing machine-specific in git** — no domains, secret values, or machine
  names. If it varies per deployment, it comes from `${VAR}` set in Dokploy.
- **Network split:** the web-facing service joins `dokploy-network` (declared
  `external: true` — created by Dokploy, never redefine it) so Traefik can reach
  it. Private dependencies (db, cache) stay on an `internal` network and are kept
  **off** `dokploy-network`, so Traefik cannot reach them.
- **Memory limits matter:** the target hosts have no swap, so `deploy.resources.limits.memory`
  is there to stop a spike from OOM-ing the box. Tune it, don't drop it.

## Config as code (when a service needs config files)

Dokploy wipes the cloned repo directory on each deploy, so runtime bind-mounts of
repo files are unreliable. The supported pattern is to **bake** config into the
image at build time:

1. Put files under `config/`.
2. In the `Dockerfile`, `COPY config/ <target>` (the build context is the freshly
   cloned repo).
3. In `docker-compose.yml`, switch from `image:` to `build: .`.

If a service needs no shipped config, **delete both** the `Dockerfile` and
`config/`.

## Validating changes

There is no build/lint/test suite. To sanity-check an edited blueprint:

```sh
docker compose config        # validates compose syntax and resolves ${VAR}
```

The real verification is the New-service checklist in `README.md` — in particular,
confirming the only `ports:` (if any) is a deliberate raw-TCP one, and that only
443 (plus any such DB port) is publicly reachable after deploy.
