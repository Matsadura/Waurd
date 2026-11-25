.PHONY: help up down build restart logs logs-back logs-front ps \
	shell-back shell-front db migrate migration seed role reset \
	install check lint format

help: ## List the commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

# --- everything ---

up: ## Start everything in the background (migrations run on backend start)
	docker compose up -d --build

down: ## Stop everything, keep the data
	docker compose down

build: ## Rebuild the images
	docker compose build

restart: ## Restart the backend and frontend (reruns migrations)
	docker compose restart backend frontend

logs: ## Follow all logs
	docker compose logs -f

ps: ## Show the containers
	docker compose ps

reset: ## Delete all data (database and Redis) and start fresh
	docker compose down -v
	docker compose up -d --build

# --- backend ---

logs-back: ## Follow the backend logs
	docker compose logs -f backend

shell-back: ## Open a shell in the backend container
	docker compose exec backend sh

db: ## Open a MySQL prompt
	docker compose exec db sh -c 'mysql -u"$$MYSQL_USER" -p"$$MYSQL_PASSWORD" "$$MYSQL_DATABASE"'

migrate: ## Apply the migrations
	docker compose exec backend alembic upgrade head

migration: ## New migration from the models: make migration m="add x to y"
	@test -n "$(m)" || (echo 'usage: make migration m="what changed"' && exit 1)
	docker compose exec -u "$$(id -u):$$(id -g)" backend alembic revision --autogenerate -m "$(m)"

seed: ## Reset and fill the database with the test users
	docker compose exec backend python scripts/seed_db.py --reset

role: ## Set a user's role: make role email=a@b.c role=GAME_MASTER
	@test -n "$(email)" -a -n "$(role)" || (echo 'usage: make role email=a@b.c role=GAME_MASTER' && exit 1)
	docker compose exec backend python scripts/set_role.py "$(email)" "$(role)"

# --- frontend ---

logs-front: ## Follow the frontend logs
	docker compose logs -f frontend

shell-front: ## Open a shell in the frontend container
	docker compose exec frontend sh

install: ## Reinstall frontend packages (after package.json changes)
	docker compose exec frontend npm ci
	docker compose restart frontend

check: ## Type-check the frontend
	docker compose exec frontend npm run check

lint: ## Check the frontend formatting
	docker compose exec frontend npm run lint

format: ## Format the frontend code
	docker compose exec frontend npm run format
