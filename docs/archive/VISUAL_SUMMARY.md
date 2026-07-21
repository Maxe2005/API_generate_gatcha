# 📊 Résumé Visuel - Système de Gestion du Cycle de Vie

## 🎯 En une image

```
                    API GATCHA - CYCLE DE VIE DES MONSTRES
                    
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  [Utilisateur] → POST /monsters/generate                           │
│                          ↓                                          │
│                  ┌───────────────┐                                  │
│                  │   GENERATED   │ ← Monstre créé                   │
│                  └───────┬───────┘                                  │
│                          │                                          │
│              ┌───────────┴───────────┐                              │
│              │                       │                              │
│          ✅ Valide              ❌ Invalide                         │
│              │                       │                              │
│              ↓                       ↓                              │
│      ┌──────────────┐        ┌──────────────┐                      │
│      │PENDING_REVIEW│        │  DEFECTIVE   │                      │
│      └──────┬───────┘        └──────┬───────┘                      │
│             │                       │                              │
│   [Admin Review]            [Admin Correct]                        │
│             │                       │                              │
│      ┌──────┴──────┐                │                              │
│      │             │                ↓                              │
│  Approve      Reject         ┌──────────────┐                      │
│      │             │         │  CORRECTED   │                      │
│      ↓             │         └──────┬───────┘                      │
│  ┌────────┐        │                │                              │
│  │APPROVED│        │                └──→ PENDING_REVIEW             │
│  └───┬────┘        ↓                                               │
│      │        ┌──────────┐                                         │
│      │        │ REJECTED │ ← État final                            │
│      │        └──────────┘                                         │
│      │                                                             │
│  [Transmit]                                                        │
│      ↓                                                             │
│  ┌─────────────┐                                                   │
│  │TRANSMITTED  │ ← État final → Disponible dans le jeu             │
│  └─────────────┘                                                   │
│      │                                                             │
│      ↓                                                             │
│  [API Invocation]                                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 📊 États et transitions

| État | Description | Transitions possibles | Acteur |
|------|-------------|----------------------|--------|
| **GENERATED** | Monstre créé avec succès | → PENDING_REVIEW | Système |
| **DEFECTIVE** | Validation technique échouée | → CORRECTED<br>→ REJECTED | Admin |
| **CORRECTED** | Défaut corrigé manuellement | → PENDING_REVIEW | Système |
| **PENDING_REVIEW** | En attente de validation admin | → APPROVED<br>→ REJECTED | Admin |
| **APPROVED** | Validé par admin | → TRANSMITTED<br>→ PENDING_REVIEW (rollback) | Admin/Système |
| **TRANSMITTED** | Transmis à l'API invocation | (final) | - |
| **REJECTED** | Rejeté définitivement | (final) | - |

## 🔄 Workflows

### Workflow 1 : Succès complet (90% des cas)

```
1. POST /monsters/generate
   └─> GENERATED (auto)
       └─> PENDING_REVIEW (auto)

2. GET /admin/monsters?state=PENDING_REVIEW
   └─> [Admin consulte]

3. POST /admin/monsters/{id}/review {"action": "approve"}
   └─> APPROVED

4. POST /transmission/transmit/{id}
   └─> TRANSMITTED ✅
```

**Durée typique :** 2-5 minutes (selon temps de review admin)

---

### Workflow 2 : Avec correction (8% des cas)

```
1. POST /monsters/generate
   └─> DEFECTIVE (validation échoue)

2. GET /admin/monsters?state=DEFECTIVE
   └─> [Admin identifie le problème]

3. POST /admin/monsters/{id}/correct {"corrected_data": {...}}
   └─> CORRECTED
       └─> PENDING_REVIEW (auto)

4. POST /admin/monsters/{id}/review {"action": "approve"}
   └─> APPROVED

5. POST /transmission/transmit/{id}
   └─> TRANSMITTED ✅
```

**Durée typique :** 5-15 minutes (correction + review)

---

### Workflow 3 : Rejet (2% des cas)

```
1. POST /monsters/generate
   └─> GENERATED
       └─> PENDING_REVIEW

2. GET /admin/monsters/{id}
   └─> [Admin examine et décide de rejeter]

3. POST /admin/monsters/{id}/review {"action": "reject", "notes": "Qualité insuffisante"}
   └─> REJECTED ❌
```

**Durée typique :** 1-3 minutes

---

## 🎨 Architecture en couches

```
┌───────────────────────────────────────────────────────────────┐
│                     🖥️  FRONTEND ADMIN                        │
│                  (À développer - Phase future)                │
└──────────────────────────────┬────────────────────────────────┘
                               │ REST API
┌──────────────────────────────▼────────────────────────────────┐
│                     📡 ENDPOINTS (FastAPI)                     │
│  /monsters/*, /admin/*, /transmission/*                       │
└──────────────────────────────┬────────────────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────────┐
│                     🔧 SERVICES LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │    Gatcha    │  │    Admin     │  │Transmission  │       │
│  │   Service    │  │   Service    │  │   Service    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└──────────────────────────────┬────────────────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────────┐
│                     ⚙️  CORE SERVICES                          │
│  ┌──────────────┐           ┌──────────────┐                 │
│  │    State     │           │  Validation  │                 │
│  │   Manager    │           │   Service    │                 │
│  └──────────────┘           └──────────────┘                 │
└──────────────────────────────┬────────────────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────────┐
│                     💾 DATA LAYER                              │
│  ┌──────────────────────────────────────────┐                 │
│  │        Monster Repository                 │                 │
│  │     (JSON → Future: PostgreSQL)          │                 │
│  └──────────────────────────────────────────┘                 │
└──────────────────────────────┬────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
┌─────────▼──────┐  ┌──────────▼─────┐  ┌──────────▼─────────┐
│  🤖 Gemini API │  │ 🍌 Banana API  │  │ 🎮 Invocation API  │
│   (Génération) │  │   (Images)     │  │   (Jeu)           │
└────────────────┘  └────────────────┘  └────────────────────┘
```

## 📈 Statistiques prévisionnelles

### Répartition des états (après 1 mois d'utilisation)

```
📊 Distribution des monstres par état

TRANSMITTED     ████████████████████████████████████████  80%  (800/1000)
PENDING_REVIEW  ████████                                   8%  (80/1000)
APPROVED        ████                                       4%  (40/1000)
DEFECTIVE       ███                                        3%  (30/1000)
REJECTED        ██                                         2%  (20/1000)
GENERATED       █                                          1%  (10/1000)
CORRECTED       █                                          1%  (10/1000)
TRANSMITTED     █                                          1%  (10/1000)
```

### Métriques clés

| Métrique | Valeur cible | Formule |
|----------|--------------|---------|
| **Taux de validation** | > 95% | (TRANSMITTED + APPROVED) / TOTAL |
| **Taux de rejet** | < 5% | REJECTED / TOTAL |
| **Temps moyen de review** | < 5 min | AVG(review_date - created_at) |
| **Taux de correction** | < 10% | CORRECTED / TOTAL |
| **Transmission rate** | > 98% | TRANSMITTED / APPROVED |

## 🔌 Intégration API Invocation

### Format de mapping

```python
# NOTRE FORMAT
{
  "nom": "Pyrolosse",
  "element": "FIRE",
  "rang": "COMMON",
  "stats": {
    "hp": 1500,
    "atk": 250,
    "def": 180,  # ou "def_"
    "vit": 120
  },
  "description_carte": "...",
  "description_visuelle": "...",
  "skills": [...]
}

# ↓ MAPPING AUTOMATIQUE ↓

# FORMAT API INVOCATION
{
  "name": "Pyrolosse",         # nom → name
  "element": "FIRE",            # ✓ identique
  "rank": "COMMON",             # rang → rank
  "stats": {
    "hp": 1500,                 # ✓ identique
    "atk": 250,                 # ✓ identique
    "def": 180,                 # def_ → def
    "vit": 120                  # ✓ identique
  },
  "cardDescription": "...",     # description_carte → cardDescription
  "visualDescription": "...",   # description_visuelle → visualDescription
  "imageUrl": "...",            # ajouté automatiquement
  "skills": [...]               # ✓ identique
}
```

### Retry logic

```
Tentative 1  →  ❌ Échec  →  Wait 2s
Tentative 2  →  ❌ Échec  →  Wait 4s
Tentative 3  →  ✅ Succès  →  TRANSMITTED

Si 3 échecs → Erreur loguée + notification admin
```

## 📂 Structure des fichiers

```
app/static/
├── images/                           # Images générées
│   └── pyrolosse.png
│
├── jsons/
│   ├── generated/                    # État: GENERATED
│   │   └── pyrolosse.json
│   ├── defective/                    # État: DEFECTIVE
│   ├── corrected/                    # État: CORRECTED
│   ├── pending_review/               # État: PENDING_REVIEW
│   │   └── salamandre.json
│   ├── approved/                     # État: APPROVED
│   │   └── dracofire.json
│   ├── transmitted/                  # État: TRANSMITTED
│   │   └── phenixflame.json
│   └── rejected/                     # État: REJECTED
│
└── metadata/                         # Métadonnées + historique
    ├── uuid-123_metadata.json        # Métadonnées de pyrolosse
    ├── uuid-456_metadata.json        # Métadonnées de salamandre
    └── ...

Exemple de métadonnées (uuid-123_metadata.json):
{
  "monster_id": "uuid-123",
  "filename": "pyrolosse.json",
  "state": "TRANSMITTED",
  "created_at": "2026-02-08T10:00:00Z",
  "transmitted_at": "2026-02-08T10:05:00Z",
  "history": [
    {"from": null, "to": "GENERATED", "timestamp": "...", "actor": "system"},
    {"from": "GENERATED", "to": "PENDING_REVIEW", "timestamp": "...", "actor": "system"},
    {"from": "PENDING_REVIEW", "to": "APPROVED", "timestamp": "...", "actor": "admin"},
    {"from": "APPROVED", "to": "TRANSMITTED", "timestamp": "...", "actor": "system"}
  ]
}
```

## 🎯 Endpoints clés

### Pour l'utilisateur (génération)

```bash
# Générer un monstre
POST /api/v1/monsters/generate
Body: {"prompt": "Dragon de feu cyberpunk"}

# Générer un batch
POST /api/v1/monsters/generate-batch
Body: {"n": 5, "prompt": "Équipe élémentaire"}
```

### Pour l'admin (gestion)

```bash
# Lister les monstres en attente
GET /api/v1/admin/monsters?state=PENDING_REVIEW&limit=20

# Voir les détails
GET /api/v1/admin/monsters/{monster_id}

# Approuver
POST /api/v1/admin/monsters/{monster_id}/review
Body: {"action": "approve", "notes": "Excellent design"}

# Corriger un défectueux
POST /api/v1/admin/monsters/{monster_id}/correct
Body: {"corrected_data": {...}}

# Transmettre
POST /api/v1/transmission/transmit/{monster_id}

# Statistiques
GET /api/v1/admin/dashboard/stats
```

## 🚀 Démarrage rapide

```bash
# 1. Installation
pip install -r requirements.txt

# 2. Configuration
cp .env.example .env
# Éditer .env avec vos clés API

# 3. Migration des données existantes
python scripts/setup_directories.py
python scripts/migrate_existing_monsters.py

# 4. Lancer l'API
uvicorn app.main:app --reload

# 5. Accéder à la documentation
open http://localhost:8000/docs

# 6. Tester
curl -X POST http://localhost:8000/api/v1/monsters/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Dragon de feu"}'
```

## ✅ Checklist d'implémentation

```
Phase 1: Fondations
  ✅ Créer les enums (MonsterState, TransitionAction)
  ✅ Créer les schémas (metadata.py, admin.py)
  ✅ Mettre à jour la config
  ✅ Créer la structure de dossiers
  ✅ Migrer les données existantes

Phase 2: Gestion des états
  ✅ Implémenter MonsterStateManager
  ✅ Implémenter MonsterRepository
  ✅ Refactorer GatchaService
  ✅ Tests unitaires

Phase 3: API Admin
  ✅ Implémenter AdminService
  ✅ Créer tous les endpoints admin
  ✅ Tester avec Swagger

Phase 4: Transmission
  ✅ Implémenter InvocationApiClient
  ✅ Implémenter TransmissionService
  ✅ Créer endpoints transmission
  ✅ Tests d'intégration

Phase 5: Refactoring
  ✅ Nettoyer le code
  ✅ Améliorer le logging
  ✅ Optimisations

Phase 6: Tests & Docs
  ✅ Tests complets
  ✅ Documentation
  ✅ Déploiement
```

## 📞 Liens rapides

- 📖 **[Stratégie globale](MONSTER_LIFECYCLE_STRATEGY.md)** - Vue d'ensemble
- 🔧 **[Spécifications techniques](TECHNICAL_SPECIFICATIONS.md)** - Code détaillé
- 🛣️ **[Roadmap d'implémentation](IMPLEMENTATION_ROADMAP.md)** - Plan d'action
- 🏛️ **[Architecture](ARCHITECTURE_DESIGN.md)** - Design et décisions
- 📋 **[Index](README_LIFECYCLE_SYSTEM.md)** - Guide de navigation

---

**Ce résumé visuel vous donne une vue d'ensemble rapide du système. Pour les détails, consultez les documents complets.**
