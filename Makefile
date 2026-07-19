.DEFAULT_GOAL := help

# Ce service se lance exclusivement via le docker-compose.yaml du projet
# orchestrateur (GatchaApi), dont ce dépôt est un sous-module.
# Il n'y a plus de docker-compose local : les cibles docker ci-dessous
# pilotent la stack racine, restreinte à ce service (et son worker Celery).
COMPOSE = docker compose -f ../docker-compose.yaml
SVC = api-generate-gatcha

.PHONY: help env install run clean seed seed-process seed-dry-run \
	db-shell db-reset db-stats db-alembic-revision db-alembic-up db-alembic-up-one db-alembic-down \
	pgadmin backup-all restore-all backup-list \
	up down down-v reset-volumes ps logs build restart \
	celery-up celery-down celery-logs celery-build celery-restart

# Variables
PYTHON = python3
VENV = .venv
BIN = $(VENV)/bin
POSTGRES_CONTAINER = postgres-generate-gatcha
POSTGRES_USER = gatcha_user
POSTGRES_DB = gatcha_db

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

env: ## Crée .env depuis .env.example s'il n'existe pas (pour le dev local uniquement)
	@test -f .env || (cp .env.example .env && echo "✅ .env créé depuis .env.example")
	@echo "ℹ️  Renseignez GEMINI_API_KEY dans .env (dev local). En docker, la config vient du .env du projet racine."

install: ## Crée l'environnement virtuel et installe les dépendances
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements.txt
	@echo "✅ Installation terminée. Activez avec 'source .venv/bin/activate'"

run: ## Lance le serveur API en local (nécessite 'make install' d'abord)
	$(BIN)/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

clean: ## Nettoie les fichiers temporaires et le venv
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -exec rm -f {} +

# ===== Docker (via la stack racine) =====

up: ## Build (if needed) and start this service (via the orchestrator stack)
	$(COMPOSE) up -d --build $(SVC)

down: ## Stop and remove this service (keeps volumes)
	$(COMPOSE) down $(SVC)

down-v: ## Stop this service and remove the stack volumes (destructive: wipes DB/minio data)
	$(COMPOSE) down -v $(SVC)

reset-volumes: ## Reset volumes and restart this service fresh
	$(COMPOSE) down -v $(SVC)
	$(COMPOSE) up -d $(SVC)

ps: ## Show status of this service's container
	$(COMPOSE) ps $(SVC)

logs: ## Tail logs for this service
	$(COMPOSE) logs -f $(SVC)

build: ## Build this service's image
	$(COMPOSE) build $(SVC)

restart: ## Rebuild and restart this service (config/code change)
	$(COMPOSE) down $(SVC)
	$(COMPOSE) up -d --build $(SVC)

celery-up: ## Start the Celery worker
	$(COMPOSE) up -d --build celery

celery-down: ## Stop the Celery worker
	$(COMPOSE) down celery

celery-logs: ## Tail logs for the Celery worker
	$(COMPOSE) logs -f celery

celery-build: ## Build the Celery worker image
	$(COMPOSE) build celery

celery-restart: ## Rebuild and restart the Celery worker
	$(COMPOSE) down celery
	$(COMPOSE) up -d --build celery

# ===== PostgreSQL =====

db-shell: ## Ouvre un shell psql dans le conteneur PostgreSQL
	docker exec -it $(POSTGRES_CONTAINER) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

db-reset: ## Reset complet de la base (⚠️  supprime toutes les données de ce service)
	@echo "⚠️  ATTENTION: Cette commande va supprimer toutes les données PostgreSQL de ce service!"
	@read -p "Êtes-vous sûr? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		$(COMPOSE) rm -sf postgres-generate-gatcha; \
		docker volume ls -q | grep postgres_generate_gatcha_data | xargs -r docker volume rm; \
		$(COMPOSE) up -d postgres-generate-gatcha; \
		sleep 5; \
		echo "✅ Base de données réinitialisée"; \
	else \
		echo "❌ Opération annulée"; \
	fi

# ===== Alembic Migrations =====

db-alembic-revision: ## Cree une migration Alembic (usage: make db-alembic-revision MSG="description")
	@bash scripts/db_migrate.sh "$(MSG)"

db-alembic-up: ## Applique les migrations Alembic (usage: make db-alembic-up REV=head)
	@bash scripts/db_upgrade.sh "$(REV)"

db-alembic-up-one: ## Applique la prochaine migration Alembic (usage: make db-alembic-up-one)
	@bash scripts/db_upgrade.sh "head"

db-alembic-down: ## Revert une migration Alembic (usage: make db-alembic-down REV=-1)
	@bash scripts/db_downgrade.sh "$(REV)"

db-stats: ## Affiche des statistiques sur la base
	@echo "📊 Statistiques de la base de données:"
	@docker exec $(POSTGRES_CONTAINER) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "\
		SELECT state, COUNT(*) as count \
		FROM monsters \
		GROUP BY state \
		ORDER BY count DESC;"

pgadmin: ## Ouvre pgAdmin dans le navigateur
	@echo "🌐 Ouverture de pgAdmin..."
	@echo "URL: http://localhost:5050"
	@echo "Email: admin@admin.com"
	@echo "Password: admin"
	@xdg-open http://localhost:5050 2>/dev/null || open http://localhost:5050 2>/dev/null || echo "Ouvrez manuellement: http://localhost:5050"

# ===== Backups (Postgres + MinIO) =====

backup-all: ## Sauvegarde Postgres et MinIO (usage: make backup-all BACKUP_NAME=nom)
	@bash scripts/backup.sh

restore-all: ## Restaure Postgres et MinIO (usage: make restore-all BACKUP_NAME=nom)
	@bash scripts/restore.sh $(BACKUP_NAME)

backup-list: ## Liste les sauvegardes disponibles
	@ls -1 backups 2>/dev/null || echo "No backups found"


# ===== Fixtures =====

seed: ## Seed les fixtures Postgres + MinIO (idempotent, config via .env)
	$(BIN)/python scripts/seed_fixtures.py

seed-process: ## Seed puis transition des monstres (PENDING_REVIEW / DEFECTIVE)
	$(BIN)/python scripts/seed_fixtures.py --process

seed-dry-run: ## Affiche le plan de seed sans toucher à la DB ni à MinIO
	$(BIN)/python scripts/seed_fixtures.py --dry-run
