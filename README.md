# Gatcha Monster Generator API

API Python modulaire basée sur FastAPI pour la génération de profils de monstres "Gatcha" via l'IA.
Ce projet utilise **Google Gemini** pour la génération de texte/stats et pour la génération d'images (Pixel Art).

L'architecture respecte les principes **SOLID** et **DRY**.

## 📋 Prérequis

- Python 3.11+
- Docker & Docker Compose (optionnel mais recommandé)
- Clé API Gemini

## 🚀 Installation & Configuration

1. **Cloner le projet**
2. **Configurer l'environnement**
   Copiez le fichier `.env` (il est déjà créé avec des placeholders) et remplissez vos clés :
   ```bash
   GEMINI_API_KEY=votre_cle_ici
   ```

## 🛠️ Utilisation Rapide (Makefile)

Un fichier `Makefile` est fourni pour simplifier les tâches courantes.

### En Local (sans Docker)

1. **Installation des dépendances** (crée aussi le venv) :
   ```bash
   make install
   ```

2. **Lancer l'API** :
   ```bash
   make run
   ```
   L'API sera accessible sur `http://localhost:8000`.

### Avec Docker (via l'orchestrateur)

Ce service se lance **exclusivement** via le dépôt orchestrateur [GatchaApi](https://github.com/Maxe2005/GatchaApi) et son `docker-compose.yaml` racine (il n'y a plus de `docker-compose.yml` local dans ce dépôt). La config docker (clés API, Postgres, Redis, MinIO) vient du `.env` **racine** du projet GatchaApi.

1. **Lancer ce service (et son worker Celery)** depuis ce dossier :
   ```bash
   make up          # rebuild + démarre api-generate-gatcha via ../docker-compose.yaml
   make celery-up   # idem pour le worker Celery
   ```

2. **Arrêter** :
   ```bash
   make down / make celery-down
   ```

En docker, l'API est exposée sur le port hôte **8084** (`http://localhost:8084/docs`).

## 📚 Documentation API

Une fois lancée, la documentation interactive est disponible aux adresses suivantes :
- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

## Logs

Les logs sont configurés pour être écrits dans `logs/app.log` avec rotation automatique (max 5MB par fichier, 3 fichiers de backup).

logs de cerlery : celery -A app.celery_worker.celery_app worker --loglevel=info

## Bases de données

Une fois lancée, l'API utilise une base de données postgreSQL ainsi qu'une base de donnée minio pour stocker les images générées. Les données de connexion sont configurables via le fichier `.env`.
- **PostgreSQL(pgAdmin)** : http://localhost:5050 (utilisateur : `admin`, mot de passe : `admin`, base de données : `gatcha_db`)
- **MinIO** : http://localhost:9000 (utilisateur : `minioadmin`, mot de passe : `minioadmin`)

## Fixtures & Seed

Le dossier `fixtures/` contient les données d'initialisation, liées 1:1 par slug :
- `fixtures/monsters/<slug>.json` : profil complet du monstre (47 fichiers) ;
- `fixtures/images/<slug>.png` : image associée quand elle existe (17 fichiers).

```bash
make seed-dry-run   # affiche le plan (aucun accès DB/MinIO requis)
make seed           # upload MinIO (raw + webp) + insertion Postgres, idempotent
make seed-process   # seed puis transition : PENDING_REVIEW (avec image) / DEFECTIVE (sans)
```

Le script utilise la configuration `.env` (surchargée par les variables d'environnement).
Les `monster_id` sont déterministes (uuid5 du nom de fichier) : relancer le seed
ne crée jamais de doublon. Pour ajouter une fixture : créer `fixtures/monsters/<slug>.json`
(et idéalement `fixtures/images/<slug>.png`, slug en ascii minuscule) puis relancer `make seed`.

## Sauvegardes (PostgreSQL + MinIO)

Les sauvegardes sont stockees dans le dossier `backups/` avec un nom horodate.

Creer une sauvegarde complete :
```bash
make backup-all
```

Creer une sauvegarde avec un nom explicite :
```bash
make backup-all BACKUP_NAME=avant_test
```

Lister les sauvegardes :
```bash
make backup-list
```

Restaurer une sauvegarde :
```bash
make restore-all BACKUP_NAME=avant_test
```

Notes :
- Par defaut, la restauration MinIO n efface pas les fichiers existants. Pour forcer une synchro stricte, utilisez `MINIO_REMOVE=true`.
- Les identifiants et le reseau Docker sont ceux du `docker-compose.yaml` racine du projet GatchaApi et peuvent etre modifies via des variables d environnement (`POSTGRES_CONTAINER`, `DOCKER_NETWORK`, ...).

## 🧪 Exemple d'Appel

**Endpoint** : `POST /api/v1/monsters/generate`

**Payload** :
```json
{
  "theme": "Cyberpunk Zombie Dragon",
  "rarity": "Legendary"
}
```

## 📂 Structure du Projet

- `app/api` : Routes et Endpoints.
- `app/clients` : Clients HTTP externes (Gemini texte/image, MinIO, API invocation, API authentification).
- `app/core` : Configuration globale.
- `app/schemas` : Modèles de données (Pydantic).
- `app/services` : Logique métier.
