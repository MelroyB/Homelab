# API Guide

FastAPI exposes OpenAPI docs at:

- `/docs`
- `/openapi.json`

## Auth model

- Access token: short-lived HttpOnly cookie (`hl_access`)
- Refresh token: HttpOnly cookie (`hl_refresh`) with rotation
- CSRF token: readable cookie (`hl_csrf`) echoed via `X-CSRF-Token`

## Endpoint groups

### Bootstrap

- `GET /api/v1/bootstrap/status`
- `POST /api/v1/bootstrap/admin`

### Auth

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/users`

### Dashboard

- `GET /api/v1/dashboard/overview`

### Services

- `GET /api/v1/services`
- `GET /api/v1/services/{slug}`
- `POST /api/v1/services/{slug}/actions`
- `GET /api/v1/services/{slug}/configs`
- `POST /api/v1/services/{slug}/configs/validate`
- `POST /api/v1/services/{slug}/configs/apply`
- `POST /api/v1/services/{slug}/configs/{version_id}/rollback`
- `GET /api/v1/services/{slug}/logs`

### Docker manager

- `GET /api/v1/docker/host`
- `GET /api/v1/docker/containers?scope=project|all`
- `POST /api/v1/docker/containers/{container_id}/actions`
- `GET /api/v1/docker/images?scope=project|all`
- `GET /api/v1/docker/images/updates?scope=project|all`
- `POST /api/v1/docker/images/pull`

### Backups

- `POST /api/v1/backups/export`
- `GET /api/v1/backups`
- `POST /api/v1/backups/restore`

### Audit and health

- `GET /api/v1/audit`
- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`

## Error conventions

- 400: validation/request errors
- 401: authentication failures
- 403: CSRF or authorization failures
- 404: resource not found
- 409: bootstrap conflict
