# Makefile for Invoice OCR project

.PHONY: help install dev test clean lint format docker-build docker-up docker-down

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pdm install

dev: ## Start development environment
	./scripts/run_dev.sh

test: ## Run tests
	pdm run pytest

test-cov: ## Run tests with coverage
	pdm run pytest --cov=ocr_app --cov=services --cov=schemas

lint: ## Run linting
	pdm run flake8 .
	pdm run mypy .

format: ## Format code
	pdm run black .
	pdm run isort .

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf build/
	rm -rf dist/

migrate: ## Run database migrations
	pdm run python manage.py migrate

makemigrations: ## Create database migrations
	pdm run python manage.py makemigrations

collectstatic: ## Collect static files
	pdm run python manage.py collectstatic --noinput

superuser: ## Create superuser
	pdm run python manage.py createsuperuser

shell: ## Start Django shell
	pdm run python manage.py shell

celery-worker: ## Start Celery worker
	pdm run celery -A invoice_ocr worker --loglevel=info

celery-beat: ## Start Celery beat
	pdm run celery -A invoice_ocr beat --loglevel=info

docker-build: ## Build Docker image
	docker-compose build

docker-up: ## Start Docker services
	docker-compose up -d

docker-down: ## Stop Docker services
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

setup: ## Initial setup
	./scripts/setup.sh

# Development shortcuts
run: ## Run Django development server
	pdm run python manage.py runserver

worker: ## Run Celery worker
	pdm run celery -A invoice_ocr worker --loglevel=info

beat: ## Run Celery beat
	pdm run celery -A invoice_ocr beat --loglevel=info
