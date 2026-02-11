# Gatcha Monster Generator API

API Python modulaire basée sur FastAPI pour la génération de profils de monstres "Gatcha" via l'IA.
Ce projet utilise **Google Gemini** pour la génération de texte/stats et **Banana.dev** pour la génération d'images (Pixel Art).

L'architecture respecte les principes **SOLID** et **DRY**.

## 📋 Prérequis

- Python 3.11+
- Docker & Docker Compose (optionnel mais recommandé)
- Clés API pour Gemini et Banana.dev

## 🚀 Installation & Configuration

1. **Cloner le projet**
2. **Configurer l'environnement**
   Copiez le fichier `.env` (il est déjà créé avec des placeholders) et remplissez vos clés :
   ```bash
   GEMINI_API_KEY=votre_cle_ici
   BANANA_API_KEY=votre_cle_ici
   BANANA_MODEL_KEY=votre_model_key_ici
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

### Avec Docker

1. **Lancer l'environnement complet** :
   ```bash
   make d-up
   ```

2. **Arrêter l'environnement** :
   ```bash
   make d-down
   ```

## 📚 Documentation API

Une fois lancée, la documentation interactive est disponible aux adresses suivantes :
- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

## Bases de données

Une fois lancée, l'API utilise une base de données postgreSQL ainsi qu'une base de donnée minio pour stocker les images générées. Les données de connexion sont configurables via le fichier `.env`.
- **PostgreSQL(pgAdmin)** : http://localhost:5050 (utilisateur : `admin`, mot de passe : `admin`, base de données : `gatcha_db`)
- **MinIO** : http://localhost:9000 (utilisateur : `minioadmin`, mot de passe : `minioadmin`)

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
- Les identifiants et le reseau Docker sont ceux de `docker-compose.yml` et peuvent etre modifies via des variables d environnement.

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
- `app/clients` : Clients HTTP externes (Gemini, Banana).
- `app/core` : Configuration globale.
- `app/schemas` : Modèles de données (Pydantic).
- `app/services` : Logique métier.
