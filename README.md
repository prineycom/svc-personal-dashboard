# svc-personal-dashboard

Personal Dashboard — a deployment blueprint for [Dokploy](https://dokploy.com).
One monorepo, one flat `docker-compose.yml`, and a set of self-hosted services
that live behind [Tailscale](https://tailscale.com) and are routed by Traefik.
A shared PostgreSQL 17 + Redis 7 back the stateful services; an external Hermes
AI agent orchestrates them over MCP.

This README is the **full setup guide** — from a blank Raspberry Pi to working
`https`/`http` subdomains. If you only want the conceptual model, read
[`CONTEXT.md`](CONTEXT.md) and the [ADRs](docs/adr/).

---

## 1. Architecture

```
svc-personal-dashboard/
├── CONTEXT.md              ← project glossary & decisions
├── docs/adr/               ← architecture decision records
├── docker-compose.yml      ← flat compose — every container in one file
├── .env.example            ← shared env vars (copy to .env)
├── services/
│   ├── vikunja/            ← tasks
│   ├── firefly-iii/        ← finances
│   ├── linkding/           ← bookmarks
│   ├── beaverhabits/       ← habits
│   ├── opentickly/         ← time tracking
│   └── infra/              ← init.sql (creates per-service databases)
└── README.md
```

### Services

| Service | Purpose | Container | Internal port | Subdomain (example) | Storage |
|---------|---------|-----------|---------------|---------------------|---------|
| [Vikunja](https://vikunja.io) | Tasks | `vikunja` | `3456` | `tasks.example.com` | Shared PG |
| [Firefly III](https://firefly-iii.org) | Finances | `firefly-app` | `8080` | `finance.example.com` | Shared PG |
| [Linkding](https://github.com/sissbruecker/linkding) | Bookmarks | `linkding` | `9090` | `bookmarks.example.com` | SQLite |
| [BeaverHabits](https://github.com/daya0576/beaverhabits) | Habits | `beaverhabits` | `8080` | `habits.example.com` | SQLite |
| [OpenTickly](https://github.com/CorrectRoadH/OpenTickly) | Time tracking | `opentickly` | `8080` | `time.example.com` | Shared PG + Redis |

Supporting containers (no public route): `postgres`, `redis`, `firefly-cron`.
Comfortably under ~1 GB idle on an 8 GB Pi 5.

### MCP layer (stage 2 — Hermes integration)

Each direction is exposed to the **Hermes** AI agent as a Model Context Protocol
server: one `mcp-<svc>` container per service, serving streamable-HTTP on port
`8000` behind the `mcp-<svc>.dashboard.example.com` subdomain (Tailscale-private,
routed in the Dokploy UI like everything else). An MCP talks to its own service
over the `internal` network; only Hermes → MCP crosses the tailnet.

| MCP | Source | Transport |
|-----|--------|-----------|
| `mcp-vikunja` | `@democratize-technology/vikunja-mcp` | bridge (supergateway) |
| `mcp-firefly` | `ghcr.io/fabianonetto/mcp-server-firefly-iii` | native HTTP image |
| `mcp-linkding` | `ghcr.io/chickenzord/linkding-mcp` | native HTTP image |
| `mcp-beaverhabits` | own FastMCP | native HTTP |
| `mcp-opentickly` | own FastMCP / Toggl-MCP fork | native HTTP |

Conventions and copy-ready compose snippets: [`docs/mcp/CONVENTIONS.md`](docs/mcp/CONVENTIONS.md).
Decision record: [`docs/adr/0007-mcp-integration-topology.md`](docs/adr/0007-mcp-integration-topology.md).
The reusable stdio→HTTP bridge image lives in [`services/_mcp/`](services/_mcp/).

### Networks

- **`dokploy-network`** (external, created by Dokploy) — every web-facing
  container joins it so Traefik can reach it.
- **`<project>-internal`** (internal: true) — DB/cache/back-end traffic only,
  no outside access.

### How traffic flows

```
Browser on the tailnet
      │  http://tasks.example.com  (DNS → Pi's Tailscale IP)
      ▼
Tailscale (WireGuard)  →  Pi :80
      ▼
dokploy-traefik  (matches Host(`tasks.example.com`))
      ▼
container on dokploy-network  (e.g. vikunja:3456)
```

> **The whole stack is private.** It is reachable only from devices in your
> tailnet. There is no public ingress; Tailscale's WireGuard mesh *is* the
> security boundary, which is why per-service logins are convenience, not the
> real perimeter (see [ADR 0001](docs/adr/0001-hybrid-architecture.md)).

---

## 2. Prerequisites

- A host (this blueprint targets a **Raspberry Pi 5 / ARM64**, 8 GB).
- A [Tailscale](https://tailscale.com) account (free tier is enough).
- A domain you control (for the subdomains). Public DNS is fine — the records
  will point at a private Tailscale IP, which only tailnet members can route to.
- A GitHub account hosting this repo (private is fine).
- SSH access to the host.

---

## 3. Step-by-step setup

### Step 1 — Install Tailscale on the host

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Follow the printed URL to authenticate. Then note the host's tailnet IP — it is
in the `100.x.y.z` (CGNAT) range:

```bash
tailscale ip -4          # e.g. 100.108.52.92
```

Install Tailscale on every device that should reach the dashboard (laptop,
phone) and enable **MagicDNS** in the [Tailscale admin → DNS](https://login.tailscale.com/admin/dns).
With MagicDNS on, your devices resolve names through `100.100.100.100`, which
forwards public names (like your domain) to upstream resolvers — so the DNS
records you create in Step 2 resolve consistently across the tailnet.

> **Why this matters:** every device that needs the dashboard must be on the
> tailnet. A device that is not in the tailnet cannot route to a `100.x` address
> and will fail to connect even though DNS resolves.

### Step 2 — Point DNS at the Tailscale IP

Create one `A` record per service, all pointing at the **host's Tailscale IP**:

```
tasks.example.com       A   100.108.52.92
finance.example.com     A   100.108.52.92
fitness.example.com     A   100.108.52.92
bookmarks.example.com   A   100.108.52.92
habits.example.com      A   100.108.52.92
time.example.com        A   100.108.52.92
```

A single wildcard `*.example.com A 100.108.52.92` also works and covers future
services. Double-check spelling — a typo (`.ocm` instead of `.com`) silently
breaks one host while the rest work.

> These records are harmless in public DNS: `100.x` addresses are not routable
> from the internet, so only your tailnet devices can actually reach them.

### Step 3 — Install Dokploy (brings Traefik with it)

On the host:

```bash
curl -sSL https://dokploy.com/install.sh | sh
```

Dokploy installs itself plus a bundled **`dokploy-traefik`** container that owns
ports **80** and **443**. Its Docker provider watches `dokploy-network` with
`exposedByDefault: false`, and it exposes two entrypoints:

- `web` → `:80`  (plain HTTP)
- `websecure` → `:443` (HTTPS via Let's Encrypt)

Open the Dokploy UI at `http://<PI-TAILSCALE-IP>:3000` and create the admin
account.

> **We use the `web` (HTTP) entrypoint only.** Let's Encrypt validates over
> HTTP-01, which requires the host to be reachable from the public internet. Our
> domains resolve to a private Tailscale IP, so ACME can never complete. HTTPS
> inside the tailnet is possible but out of scope here — see
> [Optional: HTTPS](#optional-https-inside-the-tailnet).

### Step 4 — Create the application in Dokploy

1. In Dokploy, create a **Project**, then add a **Compose** service inside it.
2. Set the source to this Git repository (`prineycom/svc-personal-dashboard`),
   branch `main`. Dokploy clones it and uses the root `docker-compose.yml`.
3. (Optional) Enable the deploy webhook so a push to `main` auto-deploys.

### Step 5 — Set environment variables

Copy [`.env.example`](.env.example) for reference and fill every secret in
**Dokploy → Environment** (not in git). The required values:

```bash
COMPOSE_PROJECT_NAME=pd
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<strong-random>

# Vikunja
VIKUNJA_DATABASE_PASSWORD=<strong-random>
VIKUNJA_SERVICE_SECRET=<random>
VIKUNJA_SERVICE_PUBLICURL=http://tasks.example.com   # MUST match the domain

# Firefly III
FIREFLY_APP_KEY=base64:$(openssl rand -base64 32)    # exactly this format
FIREFLY_DB_PASSWORD=<strong-random>
FIREFLY_STATIC_CRON_TOKEN=<random-32-chars>
FIREFLY_APP_URL=http://finance.example.com           # MUST match the domain

# Linkding (no signup page — these auto-create the first user on startup)
LD_CSRF_TRUSTED_ORIGINS=http://bookmarks.example.com # MUST match the domain
LD_SUPERUSER_NAME=admin
LD_SUPERUSER_PASSWORD=<strong-random>
```

The `*_PORT` variables (e.g. `VIKUNJA_PORT=3456`) are **optional**. Setting one
publishes that container's port on the host so you can reach it directly at
`http://<PI-TAILSCALE-IP>:<port>` — handy for debugging. Leave them empty in
production if you only want Traefik routing.

> **Public-URL / CSRF variables are mandatory, not cosmetic.** Behind a domain,
> these apps build absolute URLs and validate the request origin. If they are
> missing or wrong, the page loads but **login and POST requests fail** (403 /
> broken frontend). The defaults in `docker-compose.yml` point at the example
> domains; override them to match yours.

### Step 6 — Configure domains (Traefik routing) in the Dokploy UI

**Routing is managed in the Dokploy UI, _not_ with `traefik.*` labels in
`docker-compose.yml`.** This is a deliberate single-source decision: defining a
domain in both places puts two Traefik services on one container, and Traefik
then refuses to auto-link the routers (`cannot be linked automatically with
multiple Services`) and disables them. Pick one source — here it is the UI.

For each web service, open it in Dokploy → **Domains** → **Add Domain**:

| Service (container) | Host | **Container Port** | Entrypoint / HTTPS |
|---------------------|------|--------------------|--------------------|
| `vikunja`      | `tasks.example.com`     | `3456` | `web`, HTTPS off |
| `firefly-app`  | `finance.example.com`   | `8080` | `web`, HTTPS off |
| `linkding`     | `bookmarks.example.com` | `9090` | `web`, HTTPS off |
| `beaverhabits` | `habits.example.com`    | `8080` | `web`, HTTPS off |
| `opentickly`   | `time.example.com`      | `8080` | `web`, HTTPS off |
| `mcp-vikunja`  | `mcp-vikunja.dashboard.example.com` | `8000` | `web`, HTTPS off |

> **MCP endpoints follow the `mcp-<svc>.dashboard.example.com` pattern** and all
> serve streamable-HTTP on container port `8000`. Register them in the UI the
> same way — no `traefik.*` labels in `docker-compose.yml`. Hermes then connects
> to `https://mcp-vikunja.dashboard.example.com/mcp`.

> **Use the container-internal port, not the published host port.** Traefik
> reaches containers *inside* `dokploy-network`, so OpenTickly is `8080` (its
> internal port) — **not** `8082` (the host publish). Pointing a domain at the
> host port yields `502 Bad Gateway`.

### Step 7 — Deploy

Click **Deploy** in Dokploy (or push to `main` if the webhook is set). Dokploy
pulls the repo, renders the compose with your env, and recreates the containers.
First boot runs database migrations, so give it a minute.

### Step 8 — Verify

From the host or any tailnet device:

```bash
for h in tasks finance fitness bookmarks habits time; do
  printf '%-22s ' "$h.example.com"
  curl -s -o /dev/null -w '%{http_code}\n' -H "Host: $h.example.com" http://<PI-TAILSCALE-IP>/
done
```

Expect `200`, `302`, or `307` for each (the redirects go to a login page).
`404` means Traefik has no matching router (re-check Step 6). `502` means the
target port is wrong or the backend is still starting (Step 6 + wait).

Then open each subdomain in a browser on a tailnet device. If a name does not
resolve, flush the client DNS cache (macOS:
`sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`).

**Verify the Vikunja MCP bridge.** Generate a Vikunja API token in the Vikunja UI
(**Settings → API tokens**) and set it in `.env` as `VIKUNJA_MCP_TOKEN` — this is
the token the MCP uses to call Vikunja, distinct from `VIKUNJA_SERVICE_SECRET`.
After deploy, probe the bridge on the host:

```bash
docker compose exec mcp-vikunja wget -qO- http://localhost:8000/healthz   # → ok
```

Expect a healthy response on `/healthz` and a reachable MCP endpoint on `/mcp`.
Then, from Hermes (pointed at `https://mcp-vikunja.dashboard.example.com/mcp`),
create a Vikunja task and read it back to confirm end-to-end connectivity.

Full env reference and step-by-step (token creation, the mandatory `/api/v1`
suffix, tool-list check) — [`services/_mcp/README.md`](services/_mcp/README.md)
→ **Vikunja MCP — setup**.

### Step 9 — Create the first accounts

Most services have **no default credentials** — you register the first user
through the web UI, and that user becomes the owner/admin. One exception:

| Service | First login | Action |
|---------|-------------|--------|
| **Linkding** | No signup page; **no user exists** until you create one | Set `LD_SUPERUSER_NAME` / `LD_SUPERUSER_PASSWORD` (auto-created on startup) or run `createsuperuser` |
| Vikunja | Open registration | Register the first account |
| Firefly III | First registered account becomes owner | Register the first account |
| OpenTickly | Registration via UI | Register the first account |
| BeaverHabits | Signup of the first user | Register the first account |

Create a Linkding user by hand (if you did not set `LD_SUPERUSER_*`):

```bash
docker exec -it <linkding> python manage.py createsuperuser
```

> The stack sits behind Tailscale, so these accounts are not exposed to the
> public internet.

---

## 4. Service-specific notes

These are baked into `docker-compose.yml`/`nginx.conf`; listed here so the
reasoning is not lost.

- **Vikunja** — `VIKUNJA_SERVICE_PUBLICURL` must equal the public URL, or the
  Vue frontend calls the wrong API host and login breaks.
- **Firefly III** — needs `APP_URL` set to the domain; `TRUSTED_PROXIES: "**"`
  is already set so it honours `X-Forwarded-*` from Traefik.
- **Linkding** — `LD_CSRF_TRUSTED_ORIGINS` must include the domain for login;
  it has no signup page, so set `LD_SUPERUSER_NAME` / `LD_SUPERUSER_PASSWORD`
  to auto-create the first user (see Step 9).
- **OpenTickly** — route to internal port `8080` (see Step 6).
- **BeaverHabits** — its SQLite db lives in the named volume `beaverhabits_data`
  (persists across redeploys, like the other services). The image defaults to
  the `nobody` user, which cannot write a root-owned volume (`attempt to write a
  readonly database`), so the service runs as `user: "0:0"` (root) instead.

---

## 5. Conventions

- **Routing lives in the Dokploy UI**, never as compose `traefik.*` labels.
- **HTTP via Traefik (`web` entrypoint)** — the stack is tailnet-private, so no
  Let's Encrypt.
- **Pin image tags** — never `:latest` for anything stateful.
- **No secrets in git** — domains, passwords, and limits live in Dokploy env.
- **Memory limit on every service** — the Pi 5 has no swap.
- **Shared PostgreSQL + Redis** — one instance each, separate databases per
  service; `services/infra/init.sql` creates the databases on first boot.

---

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `404 page not found` (plain text) from Traefik | No router matches the Host | Add/repair the domain in Dokploy UI (Step 6); check for DNS typos |
| `502 Bad Gateway` | Domain points at the host port, not the container port; or backend still booting | Set the **container-internal** port; wait for first-boot migrations |
| Page loads but login/POST fails (403) | Missing/incorrect public-URL or CSRF env | Set `*_PUBLICURL` / `APP_URL` / `*CSRF_TRUSTED_ORIGINS` to the domain |
| `attempt to write a readonly database` (BeaverHabits) | Container user `nobody` can't write the root-owned volume | Run as `user: "0:0"` (already set) |
| Firefly register does nothing / `$ is not defined` | Password < 16 chars; the broken register.js (upstream) just hides the inline error | Use a password of **≥ 16 characters** |
| Domain resolves on the host but not on a laptop | Device not on the tailnet, or stale DNS cache | Join the tailnet; flush client DNS |
| Two routers per host in Traefik | Domain defined in both UI and compose labels | Remove one source (keep the UI) |

Useful inspection commands on the host:

```bash
# Which routers/services does Traefik actually know?
docker exec dokploy-traefik wget -qO- http://localhost:8080/api/http/routers
docker exec dokploy-traefik wget -qO- http://localhost:8080/api/http/services

# Traefik logs (router conflicts, etc.)
docker logs --tail 50 dokploy-traefik

# Is a container on dokploy-network, and what's its IP?
docker inspect <container> --format '{{range $n,$v := .NetworkSettings.Networks}}{{$n}}={{$v.IPAddress}} {{end}}'
```

---

## Optional: HTTPS inside the tailnet

Let's Encrypt cannot validate a private Tailscale IP. If you want `https://`,
issue certificates with Tailscale instead of ACME:

- `tailscale serve` to terminate TLS in front of a service, or
- `tailscale cert <name>.<tailnet>.ts.net` to obtain a cert and terminate TLS in
  Traefik / nginx yourself.

Either approach is independent of the Dokploy domain routing above.

---

## Resource budget

- **Peak**: ~1.3 GB RAM (on an 8 GB Pi 5)
- **Idle**: ~900 MB
- **Free**: ~6.7 GB
