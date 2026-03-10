SHELL := /bin/bash

PROJECT_NAME ?= homelab

.PHONY: help install up down restart logs ps lint format test test-backend test-frontend bootstrap-admin seed-services migrate makemigration clean

help:
	@echo "Targets:"
	@echo "  install          Install backend and frontend dependencies"
	@echo "  up               Start stack with Docker Compose"
	@echo "  down             Stop stack"
	@echo "  restart          Restart stack"
	@echo "  logs             Follow logs"
	@echo "  ps               Show compose services"
	@echo "  lint             Run lint checks"
	@echo "  format           Run formatters"
	@echo "  test             Run backend + frontend tests"
	@echo "  bootstrap-admin  Bootstrap local admin via API script"
	@echo "  seed-services    Seed service registry"
	@echo "  migrate          Run Alembic migrations to head"
	@echo "  makemigration    Create new Alembic revision (name=<slug>)"
	@echo "  clean            Remove build artifacts"

install:
	cd apps/backend && pip install -e .[dev]
	cd apps/frontend && npm install

up:
	docker compose up -d --build

down:
	docker compose down

restart: down up

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

lint:
	cd apps/backend && ruff check app tests
	cd apps/backend && ruff format --check app tests
	cd apps/frontend && npm run lint
	cd apps/frontend && npm run format:check

format:
	cd apps/backend && ruff format app tests
	cd apps/backend && ruff check --fix app tests
	cd apps/frontend && npm run format


test: test-backend test-frontend

test-backend:
	cd apps/backend && pytest -q

test-frontend:
	cd apps/frontend && npm run test -- --run

bootstrap-admin:
	cd apps/backend && python -m app.scripts.bootstrap_admin

seed-services:
	cd apps/backend && python -m app.scripts.seed_services

migrate:
	cd apps/backend && alembic upgrade head

makemigration:
	cd apps/backend && alembic revision --autogenerate -m "$(name)"

clean:
	rm -rf apps/frontend/dist apps/frontend/node_modules apps/backend/.pytest_cache apps/backend/.ruff_cache
