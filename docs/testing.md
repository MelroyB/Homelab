# Testing Strategy

## Backend

- `pytest` for API/auth/service flows
- Alembic migration smoke check (`alembic upgrade head`)
- focus areas:
  - bootstrap/login/logout/refresh
  - config validation and apply behavior
  - rollback behavior
  - audit event creation

Run:

```bash
cd apps/backend
alembic upgrade head
pytest -q
```

## Frontend

- `vitest` + Testing Library for app and route-level smoke tests
- focus areas:
  - auth route guards
  - service action and config workflows
  - backup restore UI behavior

Run:

```bash
cd apps/frontend
npm run test -- --run
```

## CI checks

- backend lint + tests
- frontend lint + format check + tests + build
- compose config validation

## Planned testing expansion

- contract tests against OpenAPI schema
- integration tests with ephemeral compose stack
- chaos testing for service restart and rollback paths
