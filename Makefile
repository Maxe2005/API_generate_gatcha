.PHONY: help install run clean docker-up docker-down db-migrate db-shell db-backup db-reset pgadmin

# Variables
PYTHON = python3
VENV = .venv
BIN = $(VENV)/bin
POSTGRES_CONTAINER = gatcha_postgres
POSTGRES_USER = gatcha_user
POSTGRES_DB = gatcha_db

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

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

d-up: ## Construit et lance les conteneurs Docker en arrière-plan
	docker-compose up -d --build
	@echo "🚀 Serveur lancé sur http://localhost:8000"

d-down: ## Arrête et supprime les conteneurs Docker
	docker-compose down

d-logs: ## Affiche les logs du conteneur API
	docker-compose logs -f api

d-restart: ## Redémarre tous les conteneurs
	docker-compose restart
	@echo "🔄 Conteneurs redémarrés"

# ===== PostgreSQL =====

db-migrate: ## Migre les données JSON vers PostgreSQL
	@echo "🔄 Migration des données JSON vers PostgreSQL..."
	$(PYTHON) scripts/migrate_json_to_postgres.py
	@echo "✅ Migration terminée"

db-migrate-dry: ## Test de migration (dry-run)
	@echo "🔍 Test de migration (dry-run)..."
	$(PYTHON) scripts/migrate_json_to_postgres.py --dry-run

db-shell: ## Ouvre un shell psql dans le conteneur PostgreSQL
	docker exec -it $(POSTGRES_CONTAINER) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

db-backup: ## Sauvegarde la base de données
	@echo "💾 Backup de la base de données..."
	docker exec $(POSTGRES_CONTAINER) pg_dump -U $(POSTGRES_USER) $(POSTGRES_DB) > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup créé"

db-restore: ## Restaure la base de données (usage: make db-restore FILE=backup.sql)
	@echo "📥 Restauration de la base de données..."
	docker exec -i $(POSTGRES_CONTAINER) psql -U $(POSTGRES_USER) $(POSTGRES_DB) < $(FILE)
	@echo "✅ Base restaurée"

db-reset: ## Reset complet de la base (⚠️  supprime toutes les données)
	@echo "⚠️  ATTENTION: Cette commande va supprimer toutes les données PostgreSQL!"
	@read -p "Êtes-vous sûr? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker-compose down -v; \
		docker-compose up -d; \
		sleep 5; \
		echo "✅ Base de données réinitialisée"; \
	else \
		echo "❌ Opération annulée"; \
	fi

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
	@echo "Email: admin@gatcha.local"
	@echo "Password: admin"
	@xdg-open http://localhost:5050 2>/dev/null || open http://localhost:5050 2>/dev/null || echo "Ouvrez manuellement: http://localhost:5050"
