# Homelab Control Plane

Production-minded monorepo scaffold for managing homelab infrastructure from one web UI.

## What this repository includes

- `apps/backend`: FastAPI API-first control plane
- `apps/frontend`: React/Vite operations dashboard
- `docker-compose.yml`: Single-node deployment stack
- `infra/`: Base configs for reverse proxy, DNS/DHCP, authoritative DNS, and NTP
- `docs/`: Architecture, security, operations, roadmap, and recovery documentation

## v1 capabilities implemented

- Admin bootstrap flow (`/onboarding`) and local admin authentication
- Cookie-based auth with refresh token rotation
- CSRF double-submit protection for mutating API routes
- Service registry with Docker-backed state, health, logs, and lifecycle actions
- Docker manager page for host/project containers and image update checks
- Config management pipeline:
  - desired config input
  - render
  - validate
  - apply
  - reload/restart
  - rollback via config versions
- Audit trail for auth/service/config/backup actions
- Backup snapshot export/import of service config versions
- Dashboard and per-service pages for operations workflows

## Quick start (development)

1. Copy environment file:

```bash
cp .env.example .env
```

2. Set secure values in `.env` (`SECRET_KEY`, `POSTGRES_PASSWORD`, `INITIAL_ADMIN_PASSWORD`).

3. Start stack:

```bash
docker compose up -d --build
```

4. Open UI:

- `http://localhost:8080` (override profile)

5. First run:

- Complete onboarding at `/onboarding` to create the first admin account.
- Database migrations are applied automatically by backend container startup.
- All persistent data is stored in one Docker volume: `homelab_data`.
- Missing service subfolders and default config files are created automatically on container startup.

## Useful commands

```bash
make up
make down
make logs
make lint
make test
make bootstrap-admin
make seed-services
make migrate
```

## Architecture at a glance

- Frontend calls backend API only
- Backend persists desired state + versioned config metadata in PostgreSQL
- Backend renders/validates configs, writes runtime config files, and triggers safe reload/restart
- Docker Socket Proxy isolates container-control access from full docker socket exposure

See [docs/architecture.md](docs/architecture.md) for details and the dependency diagram.

## Security notes

- No secrets are committed; use `.env` from `.env.example`
- Development defaults are intentionally marked; production requires overriding secrets and secure cookie flags
- `socket-proxy` limits Docker API surface for the backend

See [docs/security.md](docs/security.md).

## Publishing Automation

This repository is prepared for GitHub publishing with automated CI and release pipelines:

- CI: lint, test, build, compose validation
- Docker publish on version tags (`v*.*.*`) to GHCR
- Optional Docker Hub publish when secrets are configured
- Automatic GitHub release creation with generated release notes

See [docs/publishing.md](docs/publishing.md) for the exact setup and release flow.

To run using published images instead of local builds, use:

```bash
BACKEND_IMAGE=ghcr.io/<owner>/<repo>-backend:v0.1.0 \
FRONTEND_IMAGE=ghcr.io/<owner>/<repo>-frontend:v0.1.0 \
docker compose -f docker-compose.yml -f docker-compose.publish.yml up -d
```
