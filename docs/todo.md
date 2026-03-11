# TODO

## Critical

- [x] Replace `create_all` startup with Alembic migration flow
- [ ] Add native config validators (`named-checkzone`, `dnsmasq --test`, `ntpd -n -q` dry-run)
- [ ] Add transactional apply + rollback safety lock per service
- [x] Enforce admin-only access for all sensitive endpoints (review endpoint matrix)

## Important

- [x] Add generic per-service enable/disable lifecycle control (works for future services)
- [x] Add schema-driven forms for dnsmasq and BIND9 in Service Detail UI
- [x] Add NTP configuration form + validation flow in Service Detail UI
- [x] Add guided Caddy configuration form in Service Detail UI
- [x] Add Let's Encrypt TLS settings in Caddy guided form (domains/email/staging)
- [x] Add unified Network Stack flow (DNS + DHCP + NTP) in Settings
- [x] Add per-service network stack enable toggles with container lifecycle control (stop when disabled, start on re-enable/apply)
- [x] Add DHCP leases visibility in Settings
- [x] Add DHCP scope options and reservation management in Settings
- [x] Add manual DNS records management in Settings (`name`, `type`, `value`)
- [x] Add custom authoritative domains list for BIND nameserver zones in Settings
- [ ] Add DNS record-type specific validation/hints (A/AAAA IP validation, MX priority, SRV structure)
- [ ] Add per-domain DNS record sets and SOA/NS defaults for multi-zone operation
- [ ] Add TLS certificate expiry status and renewal diagnostics in UI
- [ ] Add WireGuard/Headscale service management for secure remote homelab access
- [ ] Add SSO gateway/IdP management (Authelia/Authentik) for downstream apps
- [ ] Add observability service pack (Prometheus + Grafana + Loki + Alertmanager)
- [ ] Add offsite backup target integration (MinIO/S3-compatible)
- [ ] Add UPS/NUT service management for power events and graceful shutdown
- [ ] Add API pagination and filtering for audit and logs
- [ ] Add config diff endpoint and frontend visual diff
- [ ] Add scheduled and retained backups
- [ ] Add service dependency graph and guarded restart ordering
- [ ] Add backend worker queue for long-running operations

## Nice to have

- [ ] WebSocket streaming for real-time service health/logs
- [ ] OIDC integration and role mapping
- [ ] Multi-user CRUD UI and password rotation workflows
- [ ] Plugin SDK documentation + examples
