# Security Policy

## Supported versions

The `main` branch is the supported security baseline for now.

## Reporting a vulnerability

Please do not create a public issue for security vulnerabilities.

Report privately through GitHub Security Advisories for this repository.
Include:

- affected component and version
- reproduction steps
- impact assessment
- suggested remediation (if available)

## Response targets

- Initial triage: within 5 business days
- Fix plan for confirmed critical/high issues: as soon as possible

## Hardening baseline

- Secrets must not be committed
- Admin-only protection on sensitive management endpoints
- Docker access only via socket proxy allow-list
- Security-impacting changes require tests and docs updates
