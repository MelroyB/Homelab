# Troubleshooting

## API returns 401 unexpectedly

- Check browser has `hl_access`, `hl_refresh`, `hl_csrf` cookies
- Verify `SECRET_KEY` stayed stable across backend restarts
- Confirm system clock is accurate (token expiry validation)

## CSRF errors on POST/PUT/DELETE

- Ensure `X-CSRF-Token` header is sent and matches `hl_csrf` cookie
- Confirm proxy does not strip custom headers

## Service actions fail (start/stop/restart)

- Check `socket-proxy` container health
- Verify target service container name matches registry metadata
- Confirm backend can reach `DOCKER_HOST`

## Config apply succeeds but service still unhealthy

- Inspect service logs in UI (`Logs` page)
- Validate rendered config format manually
- Roll back to previous version and retry with smaller change set

## Bootstrap blocked

- If admin already exists, bootstrap endpoint is locked by design
- Use existing admin credentials or reset user table in non-production only

## DNS/DHCP/NTP ports not binding

- Check host-level port conflicts (`53`, `67`, `123`)
- Verify required capabilities for service containers
- Adjust compose port mappings to local environment constraints
