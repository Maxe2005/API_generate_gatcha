.PHONY: help install run clean docker-up docker-down

# Variables
PYTHON = python3
VENV = .venv
BIN = $(VENV)/bin

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
