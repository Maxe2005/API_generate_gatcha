# Refactorisation de l'Architecture de Données - Résumé

## 📋 Vue d'ensemble

Refactorisation majeure de l'architecture de stockage des monstres pour séparer les données d'état (métadonnées) des données métier (monstre structuré).

## 🎯 Objectifs atteints

✅ **Séparation claire des responsabilités**
- Table `monsters_state` : Gère le cycle de vie et les métadonnées
- Table `monsters` : Stocke les données structurées des monstres validés
- Table `skills` : Stocke les compétences de manière normalisée

✅ **Transition JSON → Base de données structurée**
- JSON utilisé pour les états initiaux (GENERATED, DEFECTIVE, CORRECTED)
- Structuration en base lors du passage à PENDING_REVIEW
- `monster_data` devient NULL après la structuration

✅ **Service de modification dédié**
- Toute modification de monstre passe par `MonsterModificationService`
- Validation des états avant modification
- Traçabilité des changements

✅ **Principes SOLID respectés**
- **Single Responsibility** : Chaque service a une responsabilité unique
- **Open/Closed** : Architecture extensible sans modification du code existant
- **Dependency Inversion** : Services dépendent d'abstractions

## 📁 Fichiers créés

### 1. **Nouveaux modèles SQLAlchemy**
- [`app/models/monster_model.py`](app/models/monster_model.py)
  - `MonsterState` : Table d'état (anciennement `Monster`)
  - `Monster` : Table structurée pour données métier
  - `Skill` : Table des compétences
  - Enums : `ElementEnum`, `RankEnum`

### 2. **Migration Alembic**
- [`alembic/versions/20260213_1506-f1cd2ff05c53_refactor_monster_structure_split_state_.py`](alembic/versions/20260213_1506-f1cd2ff05c53_refactor_monster_structure_split_state_.py)
  - Renomme `monsters` → `monsters_state`
  - Crée tables `monsters` et `skills`
  - Met `monster_data` en nullable
  - Mise à jour des foreign keys

### 3. **Service de modification**
- [`app/services/monster_modification_service.py`](app/services/monster_modification_service.py)
  - `update_monster()` : Modifie un monstre
  - `add_skill()` : Ajoute une compétence
  - `update_skill()` : Modifie une compétence
  - `delete_skill()` : Supprime une compétence
  - `replace_all_skills()` : Remplace toutes les compétences
  - Validation des états avant modification

### 4. **Schémas Pydantic enrichis**
- [`app/schemas/monster.py`](app/schemas/monster.py)
  - `SkillStructured` : Schéma pour skill en DB
  - `SkillCreate` / `SkillUpdate` : Schémas de manipulation
  - `MonsterStructured` : Schéma pour monstre en DB
  - `MonsterCreate` / `MonsterUpdate` : Schémas de manipulation

## 🔄 Fichiers modifiés

### 1. **Repository refactorisé**
- [`app/repositories/monster_repository.py`](app/repositories/monster_repository.py)
  - Adapté pour utiliser `MonsterState` au lieu de `Monster`
  - Nouvelle méthode `create_structured_monster_from_json()`
  - `get_by_monster_id()` : Récupère l'objet DB complet

### 2. **StateManager enrichi**
- [`app/services/state_manager.py`](app/services/state_manager.py)
  - Nouvelle méthode `transition_to_pending_review()`
  - Orchestration de la transition JSON → DB
  - Méthodes utilitaires : `requires_json_data()`, `requires_structured_data()`

### 3. **Modèles images mis à jour**
- [`app/models/monster_image_model.py`](app/models/monster_image_model.py)
  - Foreign key pointant vers `monsters_state` au lieu de `monsters`

### 4. **Exports mis à jour**
- [`app/models/__init__.py`](app/models/__init__.py)
  - Exporte `MonsterState`, `Monster`, `Skill`

## 🏗️ Architecture finale

```
┌─────────────────────────────────────────────────────────────┐
│                    ÉTATS DES DONNÉES                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  GENERATED / DEFECTIVE / CORRECTED                          │
│  ├─ monster_data (JSON) : Toutes les données               │
│  ├─ tables monsters/skills : VIDES                          │
│  └─ Stockage : monsters_state.monster_data                  │
│                                                             │
│              ↓ TRANSITION (PENDING_REVIEW) ↓                │
│                                                             │
│  PENDING_REVIEW / APPROVED / TRANSMITTED / REJECTED         │
│  ├─ monster_data (JSON) : NULL                              │
│  ├─ tables monsters/skills : REMPLIES                       │
│  └─ Stockage : tables structurées                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Structure des tables

```sql
-- Table d'état et métadonnées
monsters_state
  ├─ id (PK)
  ├─ monster_id (UUID)
  ├─ state (ENUM)
  ├─ monster_data (JSON, nullable)  -- NULL après PENDING_REVIEW
  ├─ created_at, updated_at
  ├─ metadata (generated_by, is_valid, review_notes, etc.)
  └─ Relations : monster (1-to-1), history, images

-- Table structurée des monstres
monsters
  ├─ id (PK)
  ├─ monster_state_id (FK → monsters_state)
  ├─ nom, element, rang
  ├─ hp, atk, def_, vit
  ├─ description_carte, description_visuelle
  ├─ created_at, updated_at
  └─ Relations : skills (1-to-many), state (1-to-1)

-- Table des compétences
skills
  ├─ id (PK)
  ├─ monster_id (FK → monsters)
  ├─ name, description
  ├─ damage, cooldown, lvl_max, rank
  ├─ ratio_stat, ratio_percent
  ├─ created_at, updated_at
  └─ Relations : monster (many-to-1)
```

## 🔄 Workflow de transition JSON → DB

```python
# 1. Monstre créé avec état GENERATED
monster_state = MonsterState(
    monster_id="uuid-123",
    state="GENERATED",
    monster_data={"nom": "Pyrolosse", "stats": {...}, "skills": [...]},
)

# 2. Transition vers PENDING_REVIEW
state_manager = MonsterStateManager()
repository = MonsterRepository(db)

success = state_manager.transition_to_pending_review(
    monster_state_db=monster_state,
    monster_json=monster_state.monster_data,
    repository=repository,
    actor="admin",
)

# 3. Résultat après transition
monster_state.monster_data  # → NULL
monster_state.monster       # → Monster object avec skills
monster_state.state         # → PENDING_REVIEW
```

## 🛠️ Utilisation du service de modification

```python
from app.services.monster_modification_service import MonsterModificationService
from app.schemas.monster import MonsterUpdate, SkillCreate

service = MonsterModificationService(db)

# Modifier un monstre
updates = MonsterUpdate(hp=2000, atk=300)
monster = service.update_monster("uuid-123", updates, actor="admin")

# Ajouter une compétence
skill_data = SkillCreate(
    name="Boule de feu",
    description="Lance une boule de feu",
    damage=150,
    cooldown=3.0,
    lvl_max=10,
    rank="RARE",
    ratio_stat="ATK",
    ratio_percent=1.5,
)
skill = service.add_skill("uuid-123", skill_data, actor="admin")

# Modifier une compétence
updates = SkillUpdate(damage=200)
skill = service.update_skill("uuid-123", skill_id=1, updates=updates)

# Supprimer une compétence
service.delete_skill("uuid-123", skill_id=1)
```

## 🚀 Prochaines étapes

### 1. **Appliquer la migration**
```bash
# Dans Docker
docker compose exec api python -m alembic upgrade head

# Ou avec make
make db-alembic-up REV=head
```

### 2. **Adapter les endpoints API**
- Mettre à jour `app/api/v1/endpoints/admin.py` pour utiliser `MonsterModificationService`
- Créer endpoints pour modification de monstres :
  - `PATCH /api/v1/admin/monsters/{monster_id}` : Modifier un monstre
  - `POST /api/v1/admin/monsters/{monster_id}/skills` : Ajouter une skill
  - `PATCH /api/v1/admin/monsters/{monster_id}/skills/{skill_id}` : Modifier une skill
  - `DELETE /api/v1/admin/monsters/{monster_id}/skills/{skill_id}` : Supprimer une skill

### 3. **Adapter les services existants**
- `GatchaService` : Utiliser `transition_to_pending_review()` au lieu de `transition()`
- `AdminService` : Intégrer `MonsterModificationService` pour les modifications

### 4. **Tests**
- Tester la migration sur une copie de la base
- Tester les transitions d'état
- Tester le service de modification

## ⚠️ Points d'attention

1. **Migration irréversible**
   - La migration peut être annulée (`alembic downgrade`), mais les données structurées seront perdues

2. **Données existantes**
   - Les monstres existants en base restent avec `monster_data` JSON
   - Ils doivent passer par PENDING_REVIEW pour être structurés

3. **Validation**
   - Le service de modification vérifie l'état avant toute modification
   - Seuls les états PENDING_REVIEW et APPROVED sont modifiables

4. **Cohérence**
   - Un monstre doit toujours avoir au moins une skill
   - `monster_data` est NULL seulement si `monster` existe

## 📚 Documentation

- [MONSTER_LIFECYCLE_STRATEGY.md](docs/MONSTER_LIFECYCLE_STRATEGY.md) : Stratégie générale
- [ARCHITECTURE_DESIGN.md](docs/ARCHITECTURE_DESIGN.md) : Architecture détaillée
- Migration Alembic : Documentation inline dans le fichier de migration

## ✅ Vérification de la refactorisation

- [x] Modèles SQLAlchemy créés et documentés
- [x] Migration Alembic générée et testable
- [x] Service de modification implémenté avec SOLID
- [x] Repository adapté à la nouvelle structure
- [x] StateManager enrichi pour gérer la transition
- [x] Schémas Pydantic pour tous les cas d'usage
- [x] Documentation complète
- [ ] Migration appliquée en base
- [ ] Endpoints API adaptés
- [ ] Tests d'intégration

---

**Date de refactorisation** : 13 février 2026
**Auteur** : GitHub Copilot (Claude Sonnet 4.5)
**Principes appliqués** : SOLID, DRY, Modularité
