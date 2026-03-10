# ADR 0003: Cookie Auth + Refresh Rotation + CSRF

## Status

Accepted

## Context

UI and API run in same origin via reverse proxy; we need practical session security for browser clients.

## Decision

- Store access and refresh tokens in HttpOnly cookies
- Rotate refresh token on each refresh call
- Enforce CSRF double-submit token for non-safe methods

## Consequences

- Better protection against token exfiltration via JS
- CSRF requirements on all mutating requests
- Session revocation supported by persisted refresh sessions
