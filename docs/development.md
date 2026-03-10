# Development Guide

## Prerequisites

- Docker + Docker Compose plugin
- Python 3.12+
- Node 22+
- GNU Make

## Local setup

```bash
cp .env.example .env
make install
make migrate
make up
```

## Running apps without full compose

Backend:

```bash
cd apps/backend
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd apps/frontend
npm install
npm run dev
```

## Database migrations

Apply migrations:

```bash
make migrate
```

Create a new migration:

```bash
make makemigration name=add_new_column
```

Create and push a release tag:

```bash
make release-tag version=0.1.0
```

## Coding standards

- Backend: Ruff lint + format
- Frontend: ESLint + Prettier
- Favor typed contracts and explicit schema updates

## Pre-commit

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## Adding a new managed service

1. Add service metadata to `app/services/registry.py`
2. Add config template in `app/templates/<slug>.j2`
3. Add validator logic in `adapters/implementations.py`
4. Ensure compose/runtime mount for config path exists
5. Add tests and docs updates
