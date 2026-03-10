# ADR 0001: FastAPI + React/Vite + Docker Compose Monorepo

## Status

Accepted

## Context

Need a practical, maintainable, self-hosted control plane with strong typing and quick operator UX iteration.

## Decision

- Backend: FastAPI
- Frontend: React + Vite + TypeScript
- Persistence: PostgreSQL (+ Redis)
- Deployment: Docker Compose (single node)

## Consequences

- Rapid API development with built-in OpenAPI
- Clear frontend/backend separation
- Easy local dev and homelab deployment
- Migration path to Kubernetes remains open
