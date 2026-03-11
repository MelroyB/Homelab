# Deployment Guide

## Target

Single-node homelab server (Docker Engine) with persistent local storage.

## Steps

1. Clone repo
2. Create `.env` from `.env.example`
3. Set production secrets and secure flags:
   - `SECRET_KEY`
   - `POSTGRES_PASSWORD`
   - `INITIAL_ADMIN_PASSWORD` (or onboarding-only flow)
   - `AUTH_COOKIE_SECURE=true` behind TLS
   - `CSRF_COOKIE_SECURE=true` behind TLS
4. Start stack:

```bash
docker compose up -d --build
```

To deploy from published images instead of local builds:

```bash
BACKEND_IMAGE=ghcr.io/<owner>/<repo>-backend:v0.1.0 \
FRONTEND_IMAGE=ghcr.io/<owner>/<repo>-frontend:v0.1.0 \
docker compose -f docker-compose.yml -f docker-compose.publish.yml up -d
```

5. Verify readiness:

```bash
curl http://localhost:8080/api/v1/health/ready
```

## Mail stack ports

Default host mappings:

- SMTP: `MAIL_SMTP_PORT` -> `25`
- Submission: `MAIL_SUBMISSION_PORT` -> `587`
- IMAPS: `MAIL_IMAPS_PORT` -> `993`
- Webmail: `WEBMAIL_HTTP_PORT` -> `8081`

If your host already uses these ports (for example Synology DSM services), remap them in `.env`:

```env
MAIL_SMTP_PORT=2525
MAIL_SUBMISSION_PORT=2587
MAIL_IMAPS_PORT=2993
WEBMAIL_HTTP_PORT=18081
```

Then redeploy:

```bash
docker compose up -d
```

For real external mail delivery, keep public port-forwarding to standard ports (`25`, `587`, `993`) whenever possible.

## Let's Encrypt via Caddy

Configure this in the Service UI for `caddy`:

1. Enable `Let's Encrypt TLS inschakelen`
2. Add one or more domains in `Domeinen voor certificaat`
3. Set `Let's Encrypt contact e-mail`
4. Optionally enable staging mode for test issuance

Operational requirements:

- Public DNS A/AAAA records for configured domains must point to the host running Caddy.
- Inbound ports `80/tcp` and `443/tcp` must reach Caddy from the internet.
- Use staging first to avoid production rate limits while testing.

## Migrations

The backend container runs `alembic upgrade head` on startup before launching the API.
For manual control, run `make migrate` from the repo root.

## Persistence

Single named volume:

- `homelab_data`

Runtime bootstrap:

- service startup scripts auto-create required subdirectories in `homelab_data`
- default config files are copied into the volume when missing
- backend writes managed config updates into this same volume tree

## Startup order

Backend waits on `postgres`, `redis`, and `socket-proxy` health checks.
Caddy waits on frontend/backend health.

## Bootstrap

Preferred: complete onboarding via UI.
Alternative CLI:

```bash
make bootstrap-admin
```
