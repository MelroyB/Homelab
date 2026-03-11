# Roadmap

## MVP scope

- Local admin auth and onboarding
- Service registry and lifecycle actions
- Docker manager (host overview, container actions, image update checks/pull)
- Config validation/apply/versioning/rollback
- Dashboard + logs + health + backups
- Audit trail and baseline security defaults

## Phase plan

### Phase 0: repository and scaffolding (done)

- [x] Monorepo layout
- [x] CI/lint/test/tooling
- [x] Compose stack and docs

### Phase 1: auth, dashboard, service registry (in progress)

- [x] Harden auth flows (baseline)
- [x] Dashboard SLO indicators (baseline)
- [x] Generic service enable/disable lifecycle endpoint for current and future services
- [ ] richer service dependency mapping

### Phase 2: DNS and DHCP management (in progress)

- [x] dnsmasq and BIND schema-driven forms
- [x] Guided Caddy form in Service Detail UI
- [x] Let's Encrypt certificate issuance controls in guided Caddy form
- [x] Unified Network Stack profile apply for DNS + DHCP + NTP
- [x] Service enable toggles in unified Settings (`enable_dnsmasq`, `enable_bind9`, `enable_ntp`) with stop-on-disable/start-on-enable behavior
- [x] DHCP leases view and DHCP reservations management in Settings UI
- [x] Manual DNS records management in Settings UI (`A`, `AAAA`, `CNAME`, `TXT`, `MX`, `NS`, `SRV`, `PTR`, `CAA`, `NAPTR`, `SPF`, `TLSA`, `LOC`, ...)
- [x] Custom authoritative domains support in Settings (`authoritative_domains`) for BIND nameserver zones
- [ ] syntax validation by native binaries (`dnsmasq --test`, `named-checkzone`)
- [ ] safer apply with staged dry-run checks

### Phase 3: NTP and monitoring/logging (in progress)

- [x] NTP config forms + validation
- [ ] integrated observability stack (Prometheus + Grafana + Loki + Alertmanager)
- [ ] alert hooks and actionable runbooks (email/webhook)

### Phase 4: backup/restore and rollback hardening (planned)

- [ ] encrypted backup artifacts
- [ ] point-in-time restore workflows
- [ ] rollback impact simulation

### Phase 5: advanced RBAC, OIDC, HA, plugin architecture (planned)

- [ ] fine-grained roles/permissions
- [ ] OIDC providers
- [ ] HA controller architecture
- [ ] plugin SDK for third-party service adapters
- [ ] SSO gateway integration for downstream services (Authelia/Authentik)

### Phase 6: core homelab platform services (planned)

- [ ] secure remote access service (WireGuard/Headscale)
- [ ] backup target service for offsite copies (MinIO/S3-compatible)
- [ ] power event and graceful shutdown management (NUT/UPS tooling)

### Phase 7: mail platform (planned)

- [ ] Managed mail stack deployment (SMTP/IMAP + webmail)
- [ ] DKIM key generation and rotation flow
- [ ] SPF and DMARC policy helper with DNS record generation
- [ ] Mailbox CRUD (create, disable, reset password, aliases)
- [ ] Webmail integration (single sign-on/session handoff optional)
- [ ] Deliverability and abuse controls (rDNS, rate limits, fail2ban, spam policy)

## Milestones

1. M1: Secure bootstrap + auth + dashboard baseline (done)
2. M2: Safe DNS/DHCP config management (in progress)
3. M3: NTP + monitoring + log quality improvements (in progress)
4. M4: Disaster recovery hardening (planned)
5. M5: Multi-user/RBAC/OIDC + extensibility model (planned)
6. M6: Mail platform with mailbox management and webmail (planned)

## Completed foundation work

- Alembic migration baseline integrated; backend startup no longer uses runtime `create_all`.
- Guided service config forms shipped for Caddy, dnsmasq, BIND9, and NTP.
- Caddy guided flow supports Let's Encrypt domains/email/staging controls.
- Unified Settings-based Network Stack flow shipped (DNS + DHCP + NTP together).
- Unified Settings-based service toggles shipped (disable stops containers; re-enable starts before apply).
- Mail service placeholders are registered in managed services (`mailserver`, `webmail`) for lifecycle control and visibility.
- DHCP scope options, reservations, and live lease visibility shipped.
- Manual DNS record management shipped in Settings (with common record type presets).
- Custom authoritative BIND zone list shipped via Settings (`authoritative_domains`).

## Backlog (prioritized)

1. Define migration review/rollback policy and DB backup gate before destructive migrations
2. Add per-service native config lint commands before apply
3. Add secure remote-access service management (WireGuard/Headscale)
4. Add integrated observability services (Prometheus, Grafana, Loki, Alertmanager)
5. Add SSO gateway/IdP integration baseline (Authelia/Authentik + OIDC flow)
6. Add record-type specific DNS validation/hints (for example MX priority, SRV shape, IP/FQDN validation)
7. Split DNS records per authoritative domain (instead of one shared record set)
8. Add optimistic locking for concurrent config edits
9. Add diff viewer for config versions
10. Add dependency-aware service restart ordering
11. Add TLS certificate expiry/renewal visibility and diagnostics in UI
12. Add scheduled backups and retention policy
13. Add backup encryption and offsite replication
14. Add WebSocket live status/streamed logs
15. Add OIDC auth provider integration
16. Add plugin discovery and adapter loading
17. Add UPS/power orchestration (NUT) for graceful shutdown paths
18. Add managed mail stack (SMTP/IMAP + webmail + mailbox CRUD)
19. Add DKIM/SPF/DMARC guided policy and DNS publishing helper
20. Add mailbox observability (queue, delivery failures, reputation checks)

## Risks and mitigations

- Risk: Docker socket misuse
  - Mitigation: keep socket-proxy scoped; no direct docker.sock in backend
- Risk: invalid config causes outage
  - Mitigation: validation gates + staged apply + rollback
- Risk: single-node failure
  - Mitigation: frequent snapshots + restore docs + future HA phase
- Risk: credential compromise
  - Mitigation: secure cookies, CSRF checks, short access token TTL, audit trail

## Assumptions

- Single trusted homelab operator for v1
- Docker Engine available on host
- Services can be controlled through Compose-managed containers
- Local network allows required DHCP/DNS/NTP ports
- Public DNS and port-forwarding are available for external mail delivery (SMTP 25 + submission/IMAP as required)

## Out of scope (v1)

- Multi-node orchestration
- Full enterprise RBAC matrix
- External secret manager integration
- Multi-provider certificate automation beyond Caddy's built-in ACME flow

## Future enhancements

- Drift detection between desired and runtime state
- Signed config bundles and approval workflow
- Canary reload/apply for critical services
- Kubernetes controller implementation for adapters
