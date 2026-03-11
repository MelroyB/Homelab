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
- [ ] richer service dependency mapping

### Phase 2: DNS and DHCP management (in progress)

- [x] dnsmasq and BIND schema-driven forms
- [x] Guided Caddy form in Service Detail UI
- [x] Unified Network Stack profile apply for DNS + DHCP + NTP
- [x] DHCP leases view and DHCP reservations management in Settings UI
- [x] Manual DNS records management in Settings UI (`A`, `AAAA`, `CNAME`, `TXT`, `MX`, `NS`, `SRV`, `PTR`, `CAA`, `NAPTR`, `SPF`, `TLSA`, `LOC`, ...)
- [x] Custom authoritative domains support in Settings (`authoritative_domains`) for BIND nameserver zones
- [ ] syntax validation by native binaries (`dnsmasq --test`, `named-checkzone`)
- [ ] safer apply with staged dry-run checks

### Phase 3: NTP and monitoring/logging (in progress)

- [x] NTP config forms + validation
- [ ] integrated metrics stack (Prometheus/Grafana)
- [ ] alert hooks (email/webhook)

### Phase 4: backup/restore and rollback hardening (planned)

- [ ] encrypted backup artifacts
- [ ] point-in-time restore workflows
- [ ] rollback impact simulation

### Phase 5: advanced RBAC, OIDC, HA, plugin architecture (planned)

- [ ] fine-grained roles/permissions
- [ ] OIDC providers
- [ ] HA controller architecture
- [ ] plugin SDK for third-party service adapters

## Milestones

1. M1: Secure bootstrap + auth + dashboard baseline (done)
2. M2: Safe DNS/DHCP config management (in progress)
3. M3: NTP + monitoring + log quality improvements (in progress)
4. M4: Disaster recovery hardening (planned)
5. M5: Multi-user/RBAC/OIDC + extensibility model (planned)

## Completed foundation work

- Alembic migration baseline integrated; backend startup no longer uses runtime `create_all`.
- Guided service config forms shipped for Caddy, dnsmasq, BIND9, and NTP.
- Unified Settings-based Network Stack flow shipped (DNS + DHCP + NTP together).
- DHCP scope options, reservations, and live lease visibility shipped.
- Manual DNS record management shipped in Settings (with common record type presets).
- Custom authoritative BIND zone list shipped via Settings (`authoritative_domains`).

## Backlog (prioritized)

1. Define migration review/rollback policy and DB backup gate before destructive migrations
2. Add per-service native config lint commands before apply
3. Add record-type specific DNS validation/hints (for example MX priority, SRV shape, IP/FQDN validation)
4. Split DNS records per authoritative domain (instead of one shared record set)
5. Add optimistic locking for concurrent config edits
6. Add diff viewer for config versions
7. Add dependency-aware service restart ordering
8. Add scheduled backups and retention policy
9. Add backup encryption and offsite replication
10. Add WebSocket live status/streamed logs
11. Add OIDC auth provider integration
12. Add plugin discovery and adapter loading

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

## Out of scope (v1)

- Multi-node orchestration
- Full enterprise RBAC matrix
- External secret manager integration
- Automatic cert management for all domains

## Future enhancements

- Drift detection between desired and runtime state
- Signed config bundles and approval workflow
- Canary reload/apply for critical services
- Kubernetes controller implementation for adapters
