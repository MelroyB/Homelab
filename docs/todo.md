# TODO

## Critical

- [x] Replace `create_all` startup with Alembic migration flow
- [ ] Add native config validators (`named-checkzone`, `dnsmasq --test`, `ntpd -n -q` dry-run)
- [ ] Add transactional apply + rollback safety lock per service
- [x] Enforce admin-only access for all sensitive endpoints (review endpoint matrix)

## Important

- [x] Add schema-driven forms for dnsmasq and BIND9 in Service Detail UI
- [x] Add NTP configuration form + validation flow in Service Detail UI
- [x] Add guided Caddy configuration form in Service Detail UI
- [x] Add unified Network Stack flow (DNS + DHCP + NTP) in Settings
- [x] Add DHCP leases visibility in Settings
- [x] Add DHCP scope options and reservation management in Settings
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
