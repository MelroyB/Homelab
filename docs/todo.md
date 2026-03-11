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
- [x] Add managed mail settings API baseline (`/settings/mail/profile` and `/settings/mail/apply`)
- [x] Add mailbox management UI baseline in Settings (mailbox definitions + apply flow)
- [x] Add mail runtime provisioning baseline (`accounts.cf`, `aliases.cf`, `mailboxes.json`, `postfix-accounts.cf`, `postfix-virtual.cf`)
- [x] Add webmail launch URL endpoint (`/settings/mail/webmail/url`) + UI launch helper
- [x] Add guided mail domain setup check endpoint (`/settings/mail/dns/suggestions`) with DNS record preview + validation issues
- [x] Reuse mail setup validation inside `mail/apply` to block invalid apply requests
- [x] Add managed mail stack services (`mailserver`, `webmail`) in compose/runtime with persistent state
- [ ] Add post-apply smoke checks for mail stack (SMTP/IMAP/webmail reachability + auth sanity)
- [ ] Add Synology-friendly mail deployment profile with non-conflicting default host ports
- [ ] Add one-click publish of suggested mail DNS records into managed authoritative zones
- [ ] Add mailbox runtime provisioning and password rotation (apply to mail backend, not only config model)
- [ ] Add mail queue + delivery status visibility in UI
- [ ] Add DKIM key lifecycle management (generate, rotate, publish selectors)
- [ ] Add anti-abuse baseline (rate limits, fail2ban integration, relay restrictions)
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
