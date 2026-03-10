# Roadmap

## MVP scope

- Local admin auth and onboarding
- Service registry and lifecycle actions
- Docker manager (host overview, container actions, image update checks/pull)
- Config validation/apply/versioning/rollback
- Dashboard + logs + health + backups
- Audit trail and baseline security defaults

## Phase plan

### Phase 0: repository and scaffolding (current)

- Monorepo layout
- CI/lint/test/tooling
- Compose stack and docs

### Phase 1: auth, dashboard, service registry

- Harden auth flows
- Dashboard SLO indicators
- richer service dependency mapping

### Phase 2: DNS and DHCP management

- dnsmasq and BIND schema-driven forms
- syntax validation by native binaries (`dnsmasq --test`, `named-checkzone`)
- safer apply with staged dry-run checks

### Phase 3: NTP and monitoring/logging

- NTP config forms + validation
- integrated metrics stack (Prometheus/Grafana)
- alert hooks (email/webhook)

### Phase 4: backup/restore and rollback hardening

- encrypted backup artifacts
- point-in-time restore workflows
- rollback impact simulation

### Phase 5: advanced RBAC, OIDC, HA, plugin architecture

- fine-grained roles/permissions
- OIDC providers
- HA controller architecture
- plugin SDK for third-party service adapters

## Milestones

1. M1: Secure bootstrap + auth + dashboard baseline
2. M2: Safe DNS/DHCP config management
3. M3: NTP + monitoring + log quality improvements
4. M4: Disaster recovery hardening
5. M5: Multi-user/RBAC/OIDC + extensibility model

## Completed foundation work

- Alembic migration baseline integrated; backend startup no longer uses runtime `create_all`.

## Backlog (prioritized)

1. Define migration review/rollback policy and DB backup gate before destructive migrations
2. Add per-service native config lint commands before apply
3. Add optimistic locking for concurrent config edits
4. Add diff viewer for config versions
5. Add dependency-aware service restart ordering
6. Add scheduled backups and retention policy
7. Add backup encryption and offsite replication
8. Add WebSocket live status/streamed logs
9. Add OIDC auth provider integration
10. Add plugin discovery and adapter loading

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
