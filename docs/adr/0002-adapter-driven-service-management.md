# ADR 0002: Adapter-Driven Service Management

## Status

Accepted

## Context

Need to manage heterogeneous services safely while keeping vendor lock-in low.

## Decision

Define and use these interfaces:

- `ServiceAdapter`
- `ConfigRenderer`
- `ConfigValidator`
- `ServiceController`
- `HealthChecker`

## Consequences

- Each service can plug custom validation/render logic
- Control plane stays stable while service implementations evolve
- Future Kubernetes controller can swap the service controller backend
