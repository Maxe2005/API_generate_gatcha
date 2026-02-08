#!/bin/bash
# Setup script pour initialiser PostgreSQL avec pgAdmin

set -e

echo "=========================================="
echo "🚀 Setup PostgreSQL + pgAdmin"
echo "=========================================="

# Couleurs pour le terminal
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}[1/5]${NC} Vérification de Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}❌ Docker n'est pas installé${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker trouvé${NC}"

echo -e "\n${BLUE}[2/5]${NC} Vérification du fichier .env..."
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Fichier .env non trouvé, création depuis .env.example${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env créé (à éditer avec vos clés API)${NC}"
else
    echo -e "${GREEN}✓ .env existe${NC}"
fi

echo -e "\n${BLUE}[3/5]${NC} Démarrage des conteneurs..."
docker-compose down -v 2>/dev/null || true
docker-compose up -d --build
echo -e "${GREEN}✓ Conteneurs démarrés${NC}"

echo -e "\n${BLUE}[4/5]${NC} Attente du démarrage de PostgreSQL (max 30s)..."
max_attempts=30
attempt=0
while ! docker exec gatcha_postgres pg_isready -U gatcha_user &> /dev/null; do
    attempt=$((attempt + 1))
    if [ $attempt -gt $max_attempts ]; then
        echo -e "${YELLOW}❌ PostgreSQL n'a pas démarré à temps${NC}"
        exit 1
    fi
    echo "  Tentative $attempt/$max_attempts..."
    sleep 1
done
echo -e "${GREEN}✓ PostgreSQL est prêt${NC}"

echo -e "\n${BLUE}[5/5]${NC} Migration des données JSON..."
if [ -f "scripts/migrate_json_to_postgres.py" ]; then
    python3 scripts/migrate_json_to_postgres.py
    echo -e "${GREEN}✓ Migration terminée${NC}"
else
    echo -e "${YELLOW}⚠️  Script de migration non trouvé (ignoré)${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Setup terminé!${NC}"
echo "=========================================="
echo ""
echo "📍 Services disponibles:"
echo "  API:       http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo "  pgAdmin:   http://localhost:5050"
echo "  MinIO:     http://localhost:9001"
echo "  PostgreSQL: localhost:5432"
echo ""
echo "📝 Credentials pgAdmin:"
echo "  Email:    admin@gatcha.local"
echo "  Password: admin"
echo ""
echo "💾 Commandes utiles:"
echo "  make db-shell    # Ouvrir un terminal PostgreSQL"
echo "  make db-stats    # Voir les statistiques"
echo "  make pgadmin     # Ouvrir pgAdmin dans le navigateur"
echo "  make db-backup   # Sauvegarder la base"
echo ""
