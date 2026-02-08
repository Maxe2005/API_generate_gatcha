# Models - Documentation

## Structure

Ce dossier contient les modèles SQLAlchemy pour PostgreSQL.

### Fichiers

- **`base.py`**: Configuration de base SQLAlchemy
  - Création du moteur de database
  - Session factory
  - Fonction `get_db()` pour FastAPI dependency injection
  - Fonction `init_db()` pour initialiser les tables

- **`monster_model.py`**: Modèles des monstres
  - `Monster`: Table principale des monstres avec leurs données
  - `StateTransitionModel`: Historique des transitions d'état
  - `MonsterStateEnum`: Énumération des états possibles

- **`__init__.py`**: Exports publics du module

## Utilisation

### Dans un endpoint FastAPI

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.models.base import get_db

@app.get("/monsters")
def list_monsters(db: Session = Depends(get_db)):
    monsters = db.query(Monster).all()
    return monsters
```

### Dans un service

```python
from sqlalchemy.orm import Session
from app.repositories.monster_repository import MonsterRepository

class MyService:
    def __init__(self, db: Session):
        self.repo = MonsterRepository(db)
```

### Requêtes directes

```python
from app.models.base import SessionLocal
from app.models.monster_model import Monster

db = SessionLocal()
try:
    monsters = db.query(Monster).filter(
        Monster.state == MonsterStateEnum.APPROVED
    ).all()
finally:
    db.close()
```

## Schéma

### Monster

Combine les anciennes données JSON du monstre avec ses métadonnées dans une seule table.

**Champs principaux:**
- `monster_id`: UUID unique (STRING)
- `state`: État actuel (ENUM)
- `monster_data`: Données complètes du monstre (JSON)
- `is_valid`: Validation (BOOLEAN)
- `transmitted_at`: Date de transmission (TIMESTAMP)

**Relations:**
- `history`: Liste des transitions d'état (One-to-Many)

### StateTransitionModel

Historique complet des changements d'état d'un monstre.

**Champs:**
- `from_state`: État de départ
- `to_state`: État d'arrivée
- `timestamp`: Quand
- `actor`: Qui (system, admin, user)
- `note`: Pourquoi

## Index

Pour des performances optimales:
- `monster_id` (UNIQUE): Recherche rapide par ID
- `state`: Requêtes par état (GENERATED, APPROVED, etc.)
- `monster_db_id` (FK): Jointures rapides avec l'historique

## Migrations

Pour modifier le schéma, utiliser Alembic:

```bash
# Créer une migration
alembic revision --autogenerate -m "Description"

# Appliquer les migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Notes

- Le champ `monster_data` stocke tout le JSON du monstre (nom, stats, skills)
- Cela évite d'avoir des dizaines de colonnes
- PostgreSQL indexe automatiquement les champs JSON pour les requêtes
- Utiliser `->` pour accéder aux champs JSON: `monster_data->>'nom'`
