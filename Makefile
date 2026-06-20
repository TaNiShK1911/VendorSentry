# VendorSentry Makefile

.PHONY: help build up down restart logs seed test clean

help:
	@echo "VendorSentry - Development Commands"
	@echo ""
	@echo "  make build     - Build Docker images"
	@echo "  make up        - Start all services"
	@echo "  make down      - Stop all services"
	@echo "  make restart   - Restart all services"
	@echo "  make logs      - View logs (all services)"
	@echo "  make seed      - Seed the database with sample data"
	@echo "  make test      - Run tests"
	@echo "  make shell     - Open shell in API container"
	@echo "  make clean     - Remove containers and volumes"

build:
	docker compose build

up:
	docker compose up -d
	@echo "Services started. API available at http://localhost:8000"
	@echo "Swagger docs at http://localhost:8000/docs"

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f api

logs-worker:
	docker compose logs -f worker

seed:
	docker compose exec api python scripts/seed.py

test:
	docker compose exec api pytest -v

shell:
	docker compose exec api bash

clean:
	docker compose down -v
	@echo "All containers and volumes removed"

dev:
	@echo "Starting development environment..."
	make build
	make up
	@echo "Waiting for services to be ready..."
	@sleep 5
	make seed
	@echo ""
	@echo "Development environment ready!"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
