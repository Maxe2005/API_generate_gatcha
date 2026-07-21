# 📁 Fichiers à Créer - Référence Rapide

Cette liste récapitule tous les nouveaux fichiers à créer et les fichiers existants à modifier lors de l'implémentation du système de gestion du cycle de vie des monstres.

## ✨ Nouveaux fichiers à créer

### 📦 Schémas (app/schemas/)

```
app/schemas/
├── metadata.py          [NOUVEAU] Schémas de métadonnées des monstres
│   ├── StateTransition
│   ├── MonsterMetadata
│   └── MonsterWithMetadata
│
└── admin.py             [NOUVEAU] Schémas pour l'API admin
    ├── MonsterListFilter
    ├── MonsterSummary
    ├── MonsterDetail
    ├── ReviewRequest
    ├── CorrectionRequest
    ├── TransmitRequest
    ├── DashboardStats
    └── ConfigUpdate
```

### 🔧 Services (app/services/)

```
app/services/
├── state_manager.py     [NOUVEAU] Gestion des états et transitions
│   ├── StateTransitionError
│   └── MonsterStateManager
│
├── admin_service.py     [NOUVEAU] Orchestration des workflows admin
│   └── AdminService
│
└── transmission_service.py [NOUVEAU] Transmission vers API invocation
    └── TransmissionService
```

### 📊 Repository (app/repositories/)

```
app/repositories/
└── monster_repository.py [NOUVEAU] Persistance des monstres
    └── MonsterRepository
```

### 🌐 Clients (app/clients/)

```
app/clients/
└── invocation_api.py    [NOUVEAU] Client pour l'API d'invocation
    ├── InvocationApiError
    └── InvocationApiClient
```

### 🔌 Endpoints (app/api/v1/endpoints/)

```
app/api/v1/endpoints/
└── transmission.py      [NOUVEAU] Endpoints de transmission
    ├── POST /transmit/{monster_id}
    ├── POST /transmit-batch
    └── GET /health-check
```

### 🛠️ Utilitaires (app/core/)

```
app/core/
├── constants.py         [NOUVEAU] Constantes globales
│   ├── Messages d'erreur
│   ├── Messages de succès
│   ├── Limites
│   └── Timeouts
│
└── logging_config.py    [NOUVEAU] Configuration du logging
    └── setup_logging()
```

### 📜 Scripts (scripts/)

```
scripts/
├── setup_directories.py  [NOUVEAU] Crée la structure de dossiers
│   └── setup_directories()
│
└── migrate_existing_monsters.py [NOUVEAU] Migre les données existantes
    └── migrate_existing_monsters()
```

### 🧪 Tests (tests/)

```
tests/
├── test_state_manager.py    [NOUVEAU] Tests du StateManager
├── test_monster_repository.py [NOUVEAU] Tests du Repository
├── test_invocation_client.py [NOUVEAU] Tests du client API
├── test_admin_service.py    [NOUVEAU] Tests du service admin
├── test_transmission_service.py [NOUVEAU] Tests du service transmission
│
└── integration/
    └── test_full_workflow.py [NOUVEAU] Tests d'intégration complets
```

### 📚 Documentation (racine/)

```
./
├── MONSTER_LIFECYCLE_STRATEGY.md   [✅ CRÉÉ] Stratégie globale
├── TECHNICAL_SPECIFICATIONS.md     [✅ CRÉÉ] Spécifications techniques
├── IMPLEMENTATION_ROADMAP.md       [✅ CRÉÉ] Plan d'implémentation
├── ARCHITECTURE_DESIGN.md          [✅ CRÉÉ] Architecture et design
├── README_LIFECYCLE_SYSTEM.md      [✅ CRÉÉ] Index de la documentation
├── VISUAL_SUMMARY.md               [✅ CRÉÉ] Résumé visuel
├── FILES_TO_CREATE.md              [✅ CRÉÉ] Ce fichier
│
├── API_DOCUMENTATION.md            [TODO] Documentation complète des endpoints
└── DEPLOYMENT.md                   [TODO] Guide de déploiement
```

## 🔄 Fichiers existants à modifier

### Modification majeure

```
app/schemas/monster.py   [MODIFIER] Ajouter les enums
├── + MonsterState(str, Enum)
└── + TransitionAction(str, Enum)

app/services/gatcha_service.py [MODIFIER] Intégrer la gestion d'états
├── + import MonsterStateManager
├── + import MonsterRepository
└── * Modifier _process_monster_asset()

app/api/v1/endpoints/admin.py [MODIFIER/ÉTENDRE] Nouveau endpoints admin
├── * Refactorer endpoints existants
├── + GET /admin/monsters
├── + GET /admin/monsters/{id}
├── + GET /admin/monsters/{id}/history
├── + POST /admin/monsters/{id}/review
├── + POST /admin/monsters/{id}/correct
├── + GET /admin/dashboard/stats
├── + GET /admin/config
└── + PUT /admin/config

app/main.py              [MODIFIER] Enregistrer nouveaux routers
├── + from app.api.v1.endpoints import transmission
├── + app.include_router(transmission.router, ...)
└── + from app.core.logging_config import setup_logging

app/core/config.py       [MODIFIER] Ajouter nouvelles configs
├── + INVOCATION_API_URL
├── + INVOCATION_API_TIMEOUT
├── + INVOCATION_API_MAX_RETRIES
├── + INVOCATION_API_RETRY_DELAY
├── + AUTO_TRANSMIT_ENABLED
├── + AUTO_TRANSMIT_INTERVAL_SECONDS
├── + MONSTERS_BASE_PATH
└── + METADATA_DIR
```

### Modification mineure (optionnel)

```
app/utils/file_manager.py [OPTIONNEL] Nettoyer et simplifier
└── Migrer fonctionnalités vers MonsterRepository

requirements.txt         [VÉRIFIER] S'assurer que toutes les dépendances sont présentes
└── httpx (pour le client API)

.env.example             [CRÉER/MODIFIER] Exemple de configuration
├── + INVOCATION_API_URL=http://localhost:8085
└── + autres variables
```

## 📂 Structure de dossiers à créer

```bash
app/static/
├── metadata/              # Métadonnées des monstres
├── jsons/
│   ├── generated/         # État: GENERATED
│   ├── defective/         # État: DEFECTIVE (renommer depuis jsons_defective)
│   ├── corrected/         # État: CORRECTED
│   ├── pending_review/    # État: PENDING_REVIEW
│   ├── approved/          # État: APPROVED
│   ├── transmitted/       # État: TRANSMITTED
│   └── rejected/          # État: REJECTED

logs/                      # Logs applicatifs
└── app.log

scripts/                   # Scripts utilitaires
├── setup_directories.py
└── migrate_existing_monsters.py
```

## ⚡ Quick Reference - Ordre de création

### Phase 1 : Fondations (2-3h)

```bash
# 1. Schémas
touch app/schemas/metadata.py
touch app/schemas/admin.py
# Modifier app/schemas/monster.py

# 2. Configuration
# Modifier app/core/config.py

# 3. Scripts
mkdir -p scripts
touch scripts/setup_directories.py
touch scripts/migrate_existing_monsters.py
```

### Phase 2 : Gestion des états (3-4h)

```bash
# 1. Core services
touch app/services/state_manager.py

# 2. Repository
mkdir -p app/repositories
touch app/repositories/__init__.py
touch app/repositories/monster_repository.py

# 3. Tests
touch tests/test_state_manager.py
touch tests/test_monster_repository.py

# 4. Refactoring
# Modifier app/services/gatcha_service.py
```

### Phase 3 : API Admin (4-5h)

```bash
# 1. Service
touch app/services/admin_service.py

# 2. Endpoints
# Modifier app/api/v1/endpoints/admin.py

# 3. Tests
touch tests/test_admin_service.py
```

### Phase 4 : Transmission (2-3h)

```bash
# 1. Client
touch app/clients/invocation_api.py

# 2. Service
touch app/services/transmission_service.py

# 3. Endpoints
touch app/api/v1/endpoints/transmission.py

# 4. Main
# Modifier app/main.py

# 5. Tests
touch tests/test_invocation_client.py
touch tests/test_transmission_service.py
mkdir -p tests/integration
touch tests/integration/test_full_workflow.py
```

### Phase 5 : Refactoring (2-3h)

```bash
# 1. Constantes
touch app/core/constants.py

# 2. Logging
touch app/core/logging_config.py
# Modifier app/main.py

# 3. Nettoyer
# Modifier app/utils/file_manager.py (optionnel)
```

### Phase 6 : Documentation (2-3h)

```bash
# 1. Documentation API
touch API_DOCUMENTATION.md

# 2. Guide de déploiement
touch DEPLOYMENT.md

# 3. Mettre à jour README
# Modifier README.md (principal)
```

## 📊 Statistiques des fichiers

| Catégorie | Nouveaux | Modifiés | Total |
|-----------|----------|----------|-------|
| **Schémas** | 2 | 1 | 3 |
| **Services** | 3 | 1 | 4 |
| **Repositories** | 1 | 0 | 1 |
| **Clients** | 1 | 0 | 1 |
| **Endpoints** | 1 | 1 | 2 |
| **Core** | 2 | 1 | 3 |
| **Scripts** | 2 | 0 | 2 |
| **Tests** | 6 | 0 | 6 |
| **Documentation** | 8 | 1 | 9 |
| **TOTAL** | **26** | **5** | **31** |

## 🎯 Fichiers critiques (priorité haute)

Ces fichiers sont essentiels pour le fonctionnement du système :

```
1. app/schemas/metadata.py           ← Modèles de données core
2. app/schemas/admin.py              ← Schémas API admin
3. app/services/state_manager.py     ← Logique des états
4. app/repositories/monster_repository.py ← Persistance
5. app/services/admin_service.py     ← Orchestration admin
6. app/clients/invocation_api.py     ← Communication externe
7. app/services/transmission_service.py ← Transmission
8. scripts/migrate_existing_monsters.py ← Migration données
```

## 📝 Template de fichier Python

Pour chaque nouveau fichier Python, utiliser ce template :

```python
"""
Module: <nom_du_module>

Description:
<Description du module>

Author: <votre_nom>
Date: 2026-02-08
"""

from typing import ...
import logging

logger = logging.getLogger(__name__)


class MyClass:
    """
    Classe <nom>.
    
    Responsabilité:
    <Quelle est la responsabilité unique de cette classe?>
    
    Utilisation:
        >>> obj = MyClass()
        >>> result = obj.method()
    """
    
    def __init__(self):
        """Initialise l'instance"""
        pass
    
    def method(self):
        """
        Description de la méthode.
        
        Args:
            param1: Description
            
        Returns:
            Description du retour
            
        Raises:
            ErrorType: Description de l'erreur
        """
        pass
```

## 🔍 Vérification finale

Avant de considérer l'implémentation comme terminée, vérifier que tous ces fichiers existent et sont fonctionnels :

```bash
# Vérifier l'existence des fichiers critiques
ls app/schemas/metadata.py
ls app/schemas/admin.py
ls app/services/state_manager.py
ls app/repositories/monster_repository.py
ls app/services/admin_service.py
ls app/services/transmission_service.py
ls app/clients/invocation_api.py
ls app/api/v1/endpoints/transmission.py

# Vérifier les tests
pytest tests/test_state_manager.py -v
pytest tests/test_monster_repository.py -v
pytest tests/test_admin_service.py -v
pytest tests/integration/test_full_workflow.py -v

# Vérifier la structure des dossiers
ls -la app/static/jsons/pending_review/
ls -la app/static/metadata/

# Vérifier que l'API démarre
uvicorn app.main:app --reload

# Vérifier la documentation Swagger
curl http://localhost:8000/docs
```

## 🆘 Troubleshooting

### Si un fichier est manquant

```bash
# Identifier quel fichier
python -c "import app.services.state_manager"
# → Si erreur: créer app/services/state_manager.py

# Vérifier les imports
grep -r "from app.services.state_manager" app/
```

### Si les tests échouent

```bash
# Exécuter avec plus de détails
pytest tests/ -vv --tb=short

# Vérifier les dépendances
pip install -r requirements.txt

# Vérifier la config
cat .env
```

---

**Ce fichier sert de référence rapide pour savoir quels fichiers créer et dans quel ordre. Consultez la [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md) pour les détails d'implémentation de chaque fichier.**
