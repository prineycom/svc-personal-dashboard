# Report: 20-vaultwarden-password-manager

**Plan:** docs/ai/20-vaultwarden-password-manager/20-vaultwarden-password-manager-plan.md
**Mode:** inline
**Status:** ✅ complete

## Tasks

| #   | Task                                              | Status  | Commit    | Concerns |
| --- | ------------------------------------------------- | ------- | --------- | -------- |
| 1   | Add vaultwarden service + volume to compose       | ✅ DONE | `2c6df49` | —        |
| 2   | Document env vars (root + per-service .env.example)| ✅ DONE | `686edd0` | —        |
| 3   | Update CONTEXT.md (images, split, routing, totals)| ✅ DONE | `e5a6747` | —        |
| 4   | Validation (static config + isolated runtime run) | ✅ DONE | `e020186` | one doc fix, see below |

## Post-implementation

| Step          | Status     | Commit |
| ------------- | ---------- | ------ |
| Validate      | ✅ pass    | —      |
| Documentation | ⏭️ skipped | —      |
| Format        | ⏭️ N/A (no JS/lint tooling) | — |

## Runtime verification

Verified with an isolated standalone `docker run` bound to `127.0.0.1:9100` — deliberately **not** via `docker compose up`, so the container never joined the production `dokploy-network` (avoids the bare-hostname collision noted in prior memory). Image ran natively on arm64 (Pi 5).

- `docker compose config -q` → exit 0; `vaultwarden` resolves to image `vaultwarden/server:1.36.0-alpine`, target port `:80`, volume `vaultwarden_data`. ✅
- `curl http://127.0.0.1:9100/alive` → 200. ✅
- `curl http://127.0.0.1:9100/` (web vault) → 200; registration page served with `SIGNUPS_ALLOWED=true`. ✅
- `/admin` with empty `ADMIN_TOKEN` → 200 page "The admin panel is disabled…"; log confirms the panel is disabled. ✅ *(The plan predicted a 404; actual Vaultwarden behavior is a 200 "disabled" page. Behavior — admin off — is correct; the report records the real response.)*
- `/admin` with `ADMIN_TOKEN` set → 200 token-entry login form (`<input type="password">`), no "disabled" warning. ✅
- Persistence: `db.sqlite3` (size + mtime) survived a container recreate on the named `vaultwarden_data` volume. ✅

**Doc fix during verification:** the documented hash command was wrong (`vaultwarden hash` is not on `$PATH` and needs a TTY). Corrected in all three files to `docker run --rm -it vaultwarden/server /vaultwarden hash` (commit `e020186`).

## Validation

- `docker compose config -q` ✅ (exit 0)
- lint / type-check / test / build — N/A (compose-only repo, no JS or lint tooling)

## Changes summary

| File                               | Action   | Description                                                            |
| ---------------------------------- | -------- | --------------------------------------------------------------------- |
| docker-compose.yml                 | modified | Added `vaultwarden` service (1.36.0-alpine, SQLite, port 80) + volume  |
| .env.example                       | modified | Added Vaultwarden section (DOMAIN, SIGNUPS, ADMIN_TOKEN, PORT=9100)    |
| services/vaultwarden/.env.example  | created  | Per-service env doc mirroring Linkding                                 |
| CONTEXT.md                         | modified | Service Images row + totals→13, Architecture Split, Routing subdomain  |

## Commits

- `2c6df49` #20 feat(20-vaultwarden-password-manager): add vaultwarden service and volume
- `686edd0` #20 feat(20-vaultwarden-password-manager): document vaultwarden env vars
- `e5a6747` #20 docs(20-vaultwarden-password-manager): add vaultwarden to CONTEXT
- `e020186` #20 fix(20-vaultwarden-password-manager): correct ADMIN_TOKEN hash command
