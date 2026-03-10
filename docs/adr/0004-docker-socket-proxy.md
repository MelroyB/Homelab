# ADR 0004: Use Docker Socket Proxy

## Status

Accepted

## Context

The backend must manage containers but direct `/var/run/docker.sock` exposure is too broad.

## Decision

Route Docker API requests through `tecnativa/docker-socket-proxy` with limited API scope.

## Consequences

- Reduced attack surface compared to raw socket mount
- Maintains required lifecycle/log/inspect controls
- Requires explicit API allow-list changes for future capabilities
