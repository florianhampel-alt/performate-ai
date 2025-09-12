# Performate AI - Development Makefile
.PHONY: help install dev build test clean start stop restart logs shell format lint

# Default target
.DEFAULT_GOAL := help

# Colors for terminal output
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[0;33m
BLUE=\033[0;34m
PURPLE=\033[0;35m
CYAN=\033[0;36m
WHITE=\033[0;37m
NC=\033[0m # No Color

help: ## Show this help message
	@echo "$(CYAN)Performate AI Development Commands$(NC)"
	@echo "=================================="
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make $(CYAN)<target>$(NC)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(CYAN)%-15s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(PURPLE)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

install: ## Install dependencies for both frontend and backend
	@echo "$(BLUE)Installing backend dependencies...$(NC)"
	cd backend && pip install -r requirements.txt
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	cd frontend && npm install
	@echo "$(GREEN)✅ Dependencies installed successfully$(NC)"

dev: ## Start development environment
	@echo "$(BLUE)Starting development environment...$(NC)"
	docker-compose up -d redis localstack
	@echo "$(YELLOW)Waiting for services to be ready...$(NC)"
	sleep 10
	@echo "$(BLUE)Starting backend and frontend...$(NC)"
	docker-compose up backend frontend worker
	@echo "$(GREEN)✅ Development environment started$(NC)"

dev-logs: ## Show development logs
	docker-compose logs -f backend frontend worker

##@ Docker Operations

build: ## Build all Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose build --parallel
	@echo "$(GREEN)✅ Docker images built successfully$(NC)"

start: ## Start all services
	@echo "$(BLUE)Starting all services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✅ All services started$(NC)"

stop: ## Stop all services
	@echo "$(YELLOW)Stopping all services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✅ All services stopped$(NC)"

restart: ## Restart all services
	@echo "$(YELLOW)Restarting all services...$(NC)"
	docker-compose restart
	@echo "$(GREEN)✅ All services restarted$(NC)"

logs: ## Show logs from all services
	docker-compose logs -f

##@ Database and Services

redis: ## Start only Redis
	docker-compose up -d redis

localstack: ## Start only LocalStack (S3 simulation)
	docker-compose up -d localstack

services: ## Start only supporting services (Redis, LocalStack)
	docker-compose up -d redis localstack

##@ Testing and Quality

test-backend: ## Run backend tests
	@echo "$(BLUE)Running backend tests...$(NC)"
	cd backend && python -m pytest tests/ -v
	@echo "$(GREEN)✅ Backend tests completed$(NC)"

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(NC)"
	cd frontend && npm run test
	@echo "$(GREEN)✅ Frontend tests completed$(NC)"

test: test-backend test-frontend ## Run all tests

lint-backend: ## Lint backend code
	@echo "$(BLUE)Linting backend code...$(NC)"
	cd backend && black . && isort . && flake8 .
	@echo "$(GREEN)✅ Backend linting completed$(NC)"

lint-frontend: ## Lint frontend code
	@echo "$(BLUE)Linting frontend code...$(NC)"
	cd frontend && npm run lint:fix && npm run format
	@echo "$(GREEN)✅ Frontend linting completed$(NC)"

lint: lint-backend lint-frontend ## Lint all code

format: ## Format all code
	@echo "$(BLUE)Formatting code...$(NC)"
	make lint
	@echo "$(GREEN)✅ Code formatting completed$(NC)"

##@ Utilities

shell-backend: ## Open shell in backend container
	docker-compose exec backend bash

shell-frontend: ## Open shell in frontend container
	docker-compose exec frontend sh

shell-redis: ## Open Redis CLI
	docker-compose exec redis redis-cli

clean: ## Clean up development environment
	@echo "$(YELLOW)Cleaning up development environment...$(NC)"
	docker-compose down -v
	docker system prune -f
	@echo "$(GREEN)✅ Development environment cleaned$(NC)"

reset: clean install ## Reset development environment
	@echo "$(GREEN)✅ Development environment reset$(NC)"

##@ Production

prod-build: ## Build for production
	@echo "$(BLUE)Building for production...$(NC)"
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
	@echo "$(GREEN)✅ Production build completed$(NC)"

prod-up: ## Start production environment
	@echo "$(BLUE)Starting production environment...$(NC)"
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
	@echo "$(GREEN)✅ Production environment started$(NC)"

##@ Monitoring

health: ## Check health of all services
	@echo "$(BLUE)Checking service health...$(NC)"
	@echo "Backend: $(shell curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health || echo 'DOWN')"
	@echo "Frontend: $(shell curl -s -o /dev/null -w '%{http_code}' http://localhost:3000 || echo 'DOWN')"
	@echo "Redis: $(shell docker-compose exec redis redis-cli ping 2>/dev/null || echo 'DOWN')"
	@echo "LocalStack: $(shell curl -s -o /dev/null -w '%{http_code}' http://localhost:4566/health || echo 'DOWN')"

status: ## Show status of all services
	docker-compose ps

##@ Setup

init: ## Initialize project (first-time setup)
	@echo "$(BLUE)Initializing Performate AI project...$(NC)"
	@echo "$(YELLOW)1. Creating environment file...$(NC)"
	cp .env.example .env
	@echo "$(YELLOW)2. Installing dependencies...$(NC)"
	make install
	@echo "$(YELLOW)3. Building Docker images...$(NC)"
	make build
	@echo "$(GREEN)✅ Project initialized successfully!$(NC)"
	@echo "$(CYAN)Next steps:$(NC)"
	@echo "  1. Edit .env file with your API keys"
	@echo "  2. Run 'make dev' to start development"

setup-s3: ## Setup S3 buckets in LocalStack
	@echo "$(BLUE)Setting up S3 buckets...$(NC)"
	aws --endpoint-url=http://localhost:4566 s3 mb s3://performate-ai-dev-uploads
	@echo "$(GREEN)✅ S3 buckets created$(NC)"

##@ Information

info: ## Show project information
	@echo "$(CYAN)Performate AI Project Information$(NC)"
	@echo "================================="
	@echo "Backend: Python FastAPI application"
	@echo "Frontend: Next.js React application"
	@echo "Database: Redis for caching and task queue"
	@echo "Storage: S3 (LocalStack for development)"
	@echo "Worker: Celery for background tasks"
	@echo ""
	@echo "$(CYAN)Development URLs:$(NC)"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"
	@echo "LocalStack: http://localhost:4566"
