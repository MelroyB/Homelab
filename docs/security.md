# Security

## Security model (v1)

- Local admin bootstrap with hashed passwords (`argon2`)
- Cookie-based auth tokens with refresh rotation
- CSRF protection on mutating API routes (`X-CSRF-Token` + cookie)
- Admin-role enforcement on service/config/backup/audit management endpoints
- Audit logging for administrative actions
- Config validation before apply/reload
- Docker control via restricted `socket-proxy`
- Socket proxy allow-list now includes `CONTAINERS`, `INFO`, `IMAGES`, `DISTRIBUTION`, `EVENTS`, `PING`, `POST`

## Secrets handling

- No hardcoded secrets in code
- `.env.example` only; do not commit `.env`
- Rotate these before production:
  - `SECRET_KEY`
  - `POSTGRES_PASSWORD`
  - bootstrap credential values

## Container hardening (current)

- `backend` runs as non-root user
- `no-new-privileges` for backend
- network segmentation (`edge`, `control`, `infra`)
- limited Docker API exposure through proxy

## Known gaps planned for future phases

- MFA support
- OIDC SSO
- per-user RBAC permissions beyond admin role
- encrypted backups at rest (key management)
- signed config change approvals
