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

5. Verify readiness:

```bash
curl http://localhost:8080/api/v1/health/ready
```

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
