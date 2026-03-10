# Operations Runbook

## Routine commands

```bash
make ps
make logs
make restart
```

## Docker manager

- UI page: `Docker`
- API:
  - `GET /api/v1/docker/host`
  - `GET /api/v1/docker/containers?scope=project|all`
  - `POST /api/v1/docker/containers/{container_id}/actions`
  - `GET /api/v1/docker/images?scope=project|all`
  - `GET /api/v1/docker/images/updates?scope=project|all`
  - `POST /api/v1/docker/images/pull`

## Service control from API

- `POST /api/v1/services/{slug}/actions`
- Supported: `start`, `stop`, `restart`, `reload` (if service allows)

## Config change workflow

1. Validate candidate config
2. Apply candidate (creates new version)
3. Confirm health/state
4. Roll back using previous version when needed

## Health monitoring

- Liveness: `/health/live`
- Readiness: `/api/v1/health/ready`
- Dashboard surfaces service state + health + last config metadata

## Audit review

- `GET /api/v1/audit`
- Track actor, action, resource, status, and metadata

## Incident response baseline

1. Identify degraded service on dashboard
2. Inspect service logs
3. Validate current config
4. Roll back to previous known-good version
5. Capture incident notes + remediation in backlog
