# 🚀 PostgreSQL - Quick Start

## En 5 Minutes ⏱️

### 1. Démarrage Automatique (Recommandé)

```bash
./scripts/setup_postgres.sh
```

C'est tout! Le script va:
- ✅ Vérifier Docker
- ✅ Créer `.env` depuis `.env.example`
- ✅ Démarrer tous les conteneurs
- ✅ Migrer les données JSON → PostgreSQL
- ✅ Afficher les URLs et credentials

### 2. Accès à pgAdmin

Une fois le setup terminé:

1. Ouvrir http://localhost:5050
2. Login: `admin@gatcha.local` / `admin`
3. Ajouter un nouveau serveur:
   - **Host:** `postgres`
   - **Port:** `5432`
   - **Db:** `gatcha_db`
   - **User:** `gatcha_user`
   - **Password:** `gatcha_password`
4. Voir les tables `monsters` et `state_transitions`

### 3. Commandes Utiles

```bash
# Voir les stats de la DB
make db-stats

# Ouvrir un shell SQL
make db-shell

# Composer une requête personnalisée
docker exec -it gatcha_postgres psql -U gatcha_user -d gatcha_db
# Puis: SELECT * FROM monsters LIMIT 5;

# Sauvegarder la base
make db-backup

# Réinitialiser complètement
make db-reset
```

---

## Pour les Impatients 😎

```bash
# 1. Setup en une ligne
./scripts/setup_postgres.sh

# 2. Checker les données
make db-stats

# 3. Ouvrir pgAdmin
make pgadmin

# 4. Profit! 🎉
```

---

## Résolution de Problèmes Rapides

### PostgreSQL ne démarre pas
```bash
docker-compose logs postgres
# Attendre le message "ready to accept connections"
```

### "Connection refused" à pgAdmin
```bash
# Utiliser 'postgres' pas 'localhost' comme hostname
# Et vérifier le password: gatcha_password
```

### Migration a des erreurs
```bash
python scripts/migrate_json_to_postgres.py --dry-run
```

---

## URLs & Credentials

| Service | URL | Défaut |
|---------|-----|--------|
| API | http://localhost:8000 | - |
| Docs | http://localhost:8000/docs | - |
| **pgAdmin** | **http://localhost:5050** | **admin@gatcha.local / admin** |
| MinIO | http://localhost:9001 | admin / password123 |

---

## Architecture en 30 Secondes

```
┌─────────────────────────────┐
│        FastAPI (8000)       │
│      (API endpoints)        │
└──────────────┬──────────────┘
               │
       ┌───────▼────────┐
       │ SQLAlchemy ORM │
       └───────┬────────┘
               │
       ┌───────▼──────────────┐
       │   PostgreSQL (5432)  │
       │  ┌─────────────────┐ │
       │  │    monsters     │ │
       │  │ ┌─────────────┐ │ │
       │  │ │monster_data │ (JSON)
       │  │ │  (nom, stats)         │ │
       │  └─────────────────┘ │ │
       │  ┌─────────────────┐ │ │
       │  │state_transitions│ │ │
       │  │   (historique) │ │ │
       │  └─────────────────┘ │ │
       └─────────┬────────────┘
                 │
       ┌─────────▼─────────┐
       │   pgAdmin (5050)  │
       │  (Visualisation)  │
       └───────────────────┘
```

---

## Fichiers Important

- `.env` - Configuration (copie de `.env.example`)
- `docker-compose.yml` - Services Docker (API, PostgreSQL, pgAdmin, MinIO)
- `scripts/migrate_json_to_postgres.py` - Migration des données JSON
- `scripts/setup_postgres.sh` - Setup automatique
- `app/models/` - Modèles SQLAlchemy

---

## Prochaines Étapes

1. ✅ Setup avec `./scripts/setup_postgres.sh`
2. 🔍 Vérifier les données dans pgAdmin
3. 🧪 Tester les endpoints: http://localhost:8000/docs
4. 📚 Lire [MIGRATION_POSTGRESQL.md](MIGRATION_POSTGRESQL.md) pour les détails
5. 🔧 Lire [docs/POSTGRESQL_REFERENCE.md](docs/POSTGRESQL_REFERENCE.md) pour les requêtes SQL

---

## Support

- **Logs**: `docker-compose logs [service]`
- **Shell DB**: `make db-shell`
- **Stats**: `make db-stats`
- **Docs**: Voir [MIGRATION_POSTGRESQL.md](MIGRATION_POSTGRESQL.md)

**C'est tout, profitez! 🎉**
