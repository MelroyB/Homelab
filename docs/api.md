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
- `POST /api/v1/services/{slug}/enabled`
- `GET /api/v1/services/{slug}/configs`
- `POST /api/v1/services/{slug}/configs/validate`
- `POST /api/v1/services/{slug}/configs/apply`
- `POST /api/v1/services/{slug}/configs/{version_id}/rollback`
- `GET /api/v1/services/{slug}/logs`

`POST /api/v1/services/{slug}/enabled` provides generic lifecycle toggling for all current and future services:
- `enabled: false` -> marks service disabled and stops the container when running
- `enabled: true` -> marks service enabled and starts the container when it is in a stopped state

Current service catalog includes foundational placeholders for future mail management:
- `mailserver` (SMTP/IMAP)
- `webmail` (mailbox web UI)

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

### Settings

- `GET /api/v1/settings/profile`
- `GET /api/v1/settings/network/profile`
- `GET /api/v1/settings/network/dhcp/leases`
- `POST /api/v1/settings/network/apply`
- `GET /api/v1/settings/mail/profile`
- `POST /api/v1/settings/mail/dns/suggestions`
- `POST /api/v1/settings/mail/apply`
- `GET /api/v1/settings/mail/webmail/url`

`/settings/network/*` is intended as the unified management surface for:
- dnsmasq DHCP scope/options/reservations
- dnsmasq upstream resolver settings
- BIND9 zone defaults, manual DNS records (`dns_records`), and authoritative domains (`authoritative_domains`)
- NTP upstream/local-fallback settings
- service lifecycle toggles for DNS/DHCP/NTP (`enable_dnsmasq`, `enable_bind9`, `enable_ntp`)

`NetworkStackProfile` includes `authoritative_domains: string[]`:
- each value is a normalized fqdn zone name (`example.com`, `homelab.local`)
- backend ensures primary `domain` is always included in `authoritative_domains`
- invalid or duplicate domain values are filtered

`NetworkStackProfile` includes `dns_records: DnsRecord[]`:
- `name`: record name (`@`, `api`, `dashboard`, etc.)
- `type`: record type (`A`, `AAAA`, `CNAME`, `TXT`, `MX`, `NS`, `SRV`, `PTR`, `CAA`, `NAPTR`, `SPF`, `TLSA`, `LOC`, ...)
- `value`: record value (IP, hostname, text, target, ...)

When `dns_records` is empty at apply time, backend fallback keeps creating baseline `A` records from:
- `nameserver_host` / `nameserver_ip`
- `api_host` / `api_ip`
- `dashboard_host` / `dashboard_ip`

During apply, backend also writes `named.conf` with one `zone` block per `authoritative_domains` entry.

`NetworkStackProfile` includes:
- `enable_dnsmasq: boolean`
- `enable_bind9: boolean`
- `enable_ntp: boolean`

Apply behavior for each enabled flag:
- `false`: marks the managed service as disabled and stops the container when running
- `true`: marks service as enabled and attempts container start (if stopped) before config apply/reload

`NetworkServiceApplyResult.status` can include `applied`, `disabled`, `stopped`, or `failed`.

`/settings/mail/*` provides unified mail platform configuration:
- `mailserver` + `webmail` enable/disable and apply in one flow
- DKIM/SPF/DMARC profile fields
- mailbox definitions (email, password, aliases, quota, enabled)
- DNS setup check endpoint (`/settings/mail/dns/suggestions`) with blocking errors + warnings
- DNS record suggestions for `MX`, `SPF`, `DMARC`, and `DKIM`
- webmail launch URL resolution (optionally validated against a mailbox)
- mail runtime provisioning files include both generic and Docker Mailserver-compatible formats:
  - `accounts.cf`, `aliases.cf`, `mailboxes.json`
  - `postfix-accounts.cf` (`{SHA512-CRYPT}` hashes), `postfix-virtual.cf`

## Error conventions

- 400: validation/request errors
- 401: authentication failures
- 403: CSRF or authorization failures
- 404: resource not found
- 409: bootstrap conflict
