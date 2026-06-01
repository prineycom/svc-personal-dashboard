# template-service

Template for per-service **deployment blueprints** that run on
[Dokploy](https://dokploy.com). Stamp a new `svc-<name>` from this template:
Docker Compose deployed from git — **Traefik-only (no host ports)**, pinned
images, config-as-code, secrets in Dokploy env. One blueprint, deployable on any
machine.

> Two-layer model: this repo (and every `svc-*`) is a **machine-agnostic
> blueprint**. The **per-machine wiring** — domain, secrets, limits — lives only
> in each machine's Dokploy, never in git.

## Use this template

1. In GitHub repo **Settings → check "Template repository"** (one-time, on this
   repo) so it shows **"Use this template"**.
2. Create a new repo from it, named **`svc-<name>`** (e.g. `svc-litellm`).
3. Fill in the files (see checklist below) and push.
4. Deploy it on Dokploy (steps below). Push → auto-redeploy.

## Layout

```
.
├── docker-compose.yml   # the service: no host ports, on dokploy-network, pinned image, ${ENV}-driven
├── Dockerfile           # OPTIONAL — only to bake config/ into the image; else delete
├── config/              # OPTIONAL — code-managed config files baked at build time
├── .env.example         # names of env vars/secrets (values go in Dokploy)
├── .gitignore           # keeps .env / secrets out of git
└── README.md            # adapt: what the service is + its specifics
```

## Conventions (don't break these)

- **HTTP via Traefik only — no host ports for it.** Dokploy publishes container
  ports past the host firewall, so any `ports:` entry is internet-facing. Expose
  HTTP via **Traefik labels** in `docker-compose.yml` (host from `${SERVICE_DOMAIN}`).
  Use one routing method — these labels **or** Dokploy's Domains tab (which guesses
  port 3000), not both.
- **Raw TCP (a DB) is the one allowed host-port exception** — Traefik can't proxy
  it. Publish a **parameterised** port (`${DB_PUBLIC_PORT}:5432`); it's
  internet-facing, so require a strong password + host-side fail2ban. Otherwise
  keep datastores private (no `ports:`).
- **Pin image tags** (no `:latest`) — reproducible across machines and time.
- **Nothing machine-specific in git** — no domains, secrets, or machine names.
  Everything that varies comes from env set in Dokploy; reference it as `${VAR}`.
- **Secrets never committed** — `.env` is gitignored; `.env.example` lists names only.
- **Config as code** — if the service needs config files, **bake them** via the
  `Dockerfile` (runtime bind-mounts from the repo are unreliable on Dokploy).
- The web-facing service joins **`dokploy-network`**; private deps (db, cache)
  stay on an `internal` network, off `dokploy-network`.

## Deploy on Dokploy

1. **Create → Compose** service in a project.
2. **Source** = this repo (Git provider or HTTPS URL), **Branch** `main`,
   **Compose Path** `docker-compose.yml`.
3. **Environment** = the vars from `.env.example` with real values — including
   `SERVICE_DOMAIN` (the host) and `SERVICE_NAME` (a unique router id). Secrets go
   here too, never in git.
4. **Deploy.** The Traefik labels route the domain and auto-issue a Let's Encrypt
   cert (HTTP-01) within ~30–60s. For Compose you do **not** use the Domains tab.
   Auto-deploy on push is on by default.

## New-service checklist

- [ ] Repo named `svc-<name>`; this README adapted to the service.
- [ ] `docker-compose.yml`: real **pinned** image (or `build: .`), correct
      `expose:` port, required `${ENV}` mapped, memory limit tuned, healthcheck set.
- [ ] Traefik labels present; `loadbalancer.server.port` matches `expose`;
      `SERVICE_NAME` unique on the target machine.
- [ ] No `ports:` on HTTP services; the only `ports:` (if any) is a deliberate
      raw-TCP one (parameterised + strong password + fail2ban planned).
- [ ] `.env.example` lists every env var incl. `SERVICE_DOMAIN`/`SERVICE_NAME`
      (secrets included, values blank).
- [ ] If config files are needed: `config/` + `Dockerfile` (`build: .`); else both deleted.
- [ ] Deployed on Dokploy with domain + HTTPS; verified only 443 (plus any
      deliberate DB port) is public.
