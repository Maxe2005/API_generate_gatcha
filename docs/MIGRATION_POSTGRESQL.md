# Migration PostgreSQL - Guide Complet

## 🎯 Vue d'ensemble

Cette migration fait passer le système de stockage des monstres d'un système basé sur des fichiers JSON vers une vraie base de données PostgreSQL avec pgAdmin pour la visualisation.

## 🔄 Changements Majeurs

### Architecture de Persistance

**Avant:**
- Stockage des monstres en fichiers JSON dans `app/static/jsons/`
- Métadonnées séparées dans `app/static/metadata/`
- Dossiers par état (generated, approved, transmitted, etc.)
- Pas de transactions, cohérence difficile à garantir

**Après:**
- Base de données PostgreSQL relationnelle
- Table `monsters` avec données JSON intégrées
- Table `state_transitions` pour l'historique complet
- Transactions ACID garanties
- Requêtes SQL performantes avec index

### Nouveaux Services

#### PostgreSQL
- **Port:** 5432
- **Base de données:** gatcha_db
- **Utilisateur:** gatcha_user
- **Password:** gatcha_password

#### pgAdmin
- **URL:** http://localhost:5050
- **Email:** admin@gatcha.local
- **Password:** admin

## 📦 Nouveaux Fichiers

```
app/
  models/
    __init__.py          # Exports des modèles
    base.py              # Configuration SQLAlchemy
    monster_model.py     # Modèles Monster et StateTransition
    
scripts/
  migrate_json_to_postgres.py  # Script de migration

.env.example              # Template de configuration
```

## 🔧 Configuration

### 1. Variables d'Environnement

Copier `.env.example` vers `.env` et configurer:

```bash
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=gatcha_user
POSTGRES_PASSWORD=gatcha_password
POSTGRES_DB=gatcha_db
```

### 2. Dépendances Python

Nouvelles dépendances ajoutées à `requirements.txt`:
- `sqlalchemy>=2.0.0` - ORM pour PostgreSQL
- `psycopg2-binary>=2.9.0` - Driver PostgreSQL
- `alembic>=1.13.0` - Migrations de schéma (optionnel)

## 🚀 Installation et Migration

### Étape 1: Arrêter l'application existante

```bash
docker-compose down
```

### Étape 2: Installer les dépendances

```bash
pip install -r requirements.txt
```

### Étape 3: Démarrer les services avec PostgreSQL

```bash
docker-compose up -d
```

Cela démarre:
- API (port 8000)
- PostgreSQL (port 5432)
- pgAdmin (port 5050)
- MinIO (ports 9000, 9001)

### Étape 4: Vérifier que la DB est prête

```bash
docker-compose logs postgres
# Attendre: "database system is ready to accept connections"
```

### Étape 5: Migrer les données existantes

```bash
# Dry run pour vérifier
python scripts/migrate_json_to_postgres.py --dry-run

# Migration réelle
python scripts/migrate_json_to_postgres.py
```

Le script va:
- Lire tous les fichiers metadata JSON
- Trouver les fichiers monster JSON correspondants
- Créer les entrées dans PostgreSQL
- Migrer l'historique des transitions

### Étape 6: Vérifier la migration

Accéder à pgAdmin: http://localhost:5050

1. Se connecter avec `admin@gatcha.local` / `admin`
2. Ajouter un serveur:
   - **Host:** postgres
   - **Port:** 5432
   - **Database:** gatcha_db
   - **Username:** gatcha_user
   - **Password:** gatcha_password
3. Explorer les tables `monsters` et `state_transitions`

## 📊 Schéma de Base de Données

### Table: monsters

| Colonne | Type | Description |
|---------|------|-------------|
| id | INTEGER | Clé primaire auto-incrémentée |
| monster_id | STRING | UUID unique du monstre |
| filename | STRING | Nom du fichier original |
| state | ENUM | État actuel (GENERATED, APPROVED, etc.) |
| monster_data | JSON | Toutes les données du monstre (nom, stats, skills) |
| created_at | TIMESTAMP | Date de création |
| updated_at | TIMESTAMP | Dernière modification |
| generated_by | STRING | Source de génération (gemini, etc.) |
| generation_prompt | TEXT | Prompt utilisé |
| is_valid | BOOLEAN | Validation réussie? |
| validation_errors | JSON | Erreurs de validation |
| reviewed_by | STRING | Nom de l'admin reviewer |
| review_date | TIMESTAMP | Date de review |
| review_notes | TEXT | Notes de review |
| transmitted_at | TIMESTAMP | Date de transmission |
| transmission_attempts | INTEGER | Nombre de tentatives |
| last_transmission_error | TEXT | Dernière erreur |
| invocation_api_id | STRING | ID dans l'API d'invocation |
| image_path | STRING | Chemin de l'image |
| metadata_extra | JSON | Métadonnées additionnelles |

**Index:**
- `monster_id` (UNIQUE)
- `state`

### Table: state_transitions

| Colonne | Type | Description |
|---------|------|-------------|
| id | INTEGER | Clé primaire |
| monster_db_id | INTEGER | FK vers monsters(id) |
| from_state | ENUM | État de départ |
| to_state | ENUM | État d'arrivée |
| timestamp | TIMESTAMP | Date de transition |
| actor | STRING | Acteur (system, admin, user) |
| note | TEXT | Note descriptive |

**Index:**
- `monster_db_id`

## 🔍 Utilisation de pgAdmin

### Se connecter à la base

1. Ouvrir http://localhost:5050
2. Login: `admin@gatcha.local` / `admin`
3. Ajouter un nouveau serveur (clic droit sur Servers)
4. Onglet General:
   - Name: Gatcha DB
5. Onglet Connection:
   - Host: `postgres`
   - Port: `5432`
   - Database: `gatcha_db`
   - Username: `gatcha_user`
   - Password: `gatcha_password`

### Requêtes Utiles

**Compter les monstres par état:**
```sql
SELECT state, COUNT(*) as count
FROM monsters
GROUP BY state
ORDER BY count DESC;
```

**Voir l'historique d'un monstre:**
```sql
SELECT m.monster_id, m.monster_data->>'nom' as name,
       st.from_state, st.to_state, st.timestamp, st.actor, st.note
FROM monsters m
JOIN state_transitions st ON m.id = st.monster_db_id
WHERE m.monster_id = 'YOUR_MONSTER_ID'
ORDER BY st.timestamp;
```

**Monstres avec erreurs de validation:**
```sql
SELECT monster_id, filename, monster_data->>'nom' as name,
       validation_errors
FROM monsters
WHERE is_valid = false;
```

**Monstres récemment générés:**
```sql
SELECT monster_id, monster_data->>'nom' as name,
       monster_data->>'element' as element,
       monster_data->>'rang' as rank,
       state, created_at
FROM monsters
ORDER BY created_at DESC
LIMIT 10;
```

## 🛠️ Développement

### Accès Direct à la DB

```bash
# Via Docker
docker exec -it gatcha_postgres psql -U gatcha_user -d gatcha_db

# Commandes psql utiles
\dt              # Lister les tables
\d monsters      # Décrire la table monsters
\q               # Quitter
```

### Backup de la Database

```bash
# Exporter
docker exec gatcha_postgres pg_dump -U gatcha_user gatcha_db > backup.sql

# Restaurer
docker exec -i gatcha_postgres psql -U gatcha_user gatcha_db < backup.sql
```

### Reset de la Database

```bash
docker-compose down -v  # Supprime les volumes
docker-compose up -d
python scripts/migrate_json_to_postgres.py
```

## ⚠️ Points d'Attention

### Données Existantes

- Les fichiers JSON originaux **ne sont pas supprimés** par la migration
- Ils restent dans `app/static/` comme backup
- Après validation, vous pouvez les archiver

### Performance

- Les requêtes SQL sont beaucoup plus rapides que la lecture de fichiers
- Index sur `monster_id` et `state` pour des performances optimales
- Pool de connexions configuré (10 connexions, max 20)

### Transactions

- Toutes les opérations utilisent des transactions
- En cas d'erreur, rollback automatique
- Plus de problèmes de cohérence entre metadata et monster data

## 🔄 Rollback (si nécessaire)

Si vous devez revenir aux fichiers JSON:

1. Les fichiers originaux sont toujours dans `app/static/`
2. Checkout le commit précédent la migration
3. Redémarrer avec `docker-compose down && docker-compose up`

## 📚 Documentation API

Les endpoints API restent **identiques**, seule la couche de persistance change:

- `GET /api/v1/admin/monsters` - Liste des monstres
- `GET /api/v1/admin/monsters/{id}` - Détails d'un monstre
- `POST /api/v1/admin/monsters/{id}/review` - Review
- `POST /api/v1/transmission/transmit/{id}` - Transmission

## 🎉 Avantages de la Migration

✅ **Performance:** Requêtes SQL beaucoup plus rapides que lecture de fichiers  
✅ **Fiabilité:** Transactions ACID, pas de corruption de données  
✅ **Requêtes:** SQL puissant pour analytics et recherches complexes  
✅ **Scalabilité:** PostgreSQL peut gérer des millions de monstres  
✅ **Visualisation:** pgAdmin pour explorer et analyser les données  
✅ **Backup:** Outils professionnels de backup PostgreSQL  
✅ **Historique:** Tracking complet avec state_transitions  

## 🐛 Troubleshooting

### Problème: "Connection refused" à PostgreSQL

```bash
# Vérifier que PostgreSQL démarre bien
docker-compose logs postgres

# Attendre le healthcheck
docker-compose ps
```

### Problème: Migration échoue

```bash
# Vérifier les logs
python scripts/migrate_json_to_postgres.py 2>&1 | tee migration.log

# Vérifier la structure
docker exec -it gatcha_postgres psql -U gatcha_user -d gatcha_db -c "\dt"
```

### Problème: pgAdmin ne se connecte pas

- Utiliser `postgres` comme hostname (pas `localhost`)
- Vérifier que les services sont sur le même réseau Docker

## 📞 Support

Pour toute question sur la migration, consultez:
- Logs: `docker-compose logs`
- Database: pgAdmin http://localhost:5050
- API Docs: http://localhost:8000/docs
