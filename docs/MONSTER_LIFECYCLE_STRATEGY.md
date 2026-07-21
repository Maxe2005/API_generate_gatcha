# Stratégie de Gestion du Cycle de Vie des Monstres

## 📋 Vue d'ensemble

Ce document présente la stratégie complète pour gérer le cycle de vie des monstres, depuis leur génération jusqu'à leur transfert vers l'API d'invocation, en passant par la validation administrative.

## 🎯 Objectifs

1. **Traçabilité complète** : Suivre l'état de chaque monstre tout au long de son cycle de vie
2. **Validation humaine** : Permettre à un admin de valider ou rejeter les monstres avant leur transfert
3. **Intégration modulaire** : Communiquer avec l'API d'invocation de manière fiable
4. **Interface admin** : Fournir des endpoints REST complets pour un futur frontend
5. **Respect des principes** : SOLID, DRY, modularité, maintenabilité

## 🔄 Machine à États des Monstres

### États proposés

```
GENERATED (généré)
    ↓
DEFECTIVE (défectueux) ──→ CORRECTED (corrigé)
    ↓                           ↓
PENDING_REVIEW (en attente) ←──┘
    ↓
APPROVED (approuvé par admin)
    ↓
TRANSMITTED (transmis à l'API invocation)
    ↓
REJECTED (rejeté définitivement)
```

### Description des états

| État | Description | Actions possibles |
|------|-------------|-------------------|
| `GENERATED` | Monstre généré avec succès et validation technique OK | → PENDING_REVIEW |
| `DEFECTIVE` | Échec de validation technique (JSON invalide) | → CORRECTED, → REJECTED |
| `CORRECTED` | Monstre défectueux corrigé manuellement | → PENDING_REVIEW |
| `PENDING_REVIEW` | En attente de validation par un admin | → APPROVED, → REJECTED |
| `APPROVED` | Validé par l'admin, prêt pour transmission | → TRANSMITTED |
| `TRANSMITTED` | Transmis avec succès à l'API d'invocation | (état final) |
| `REJECTED` | Rejeté définitivement par l'admin | (état final) |

### Transitions interdites

- `TRANSMITTED` ne peut pas revenir en arrière
- `REJECTED` ne peut pas revenir en arrière
- `GENERATED` ne peut pas aller directement à `APPROVED`

## 🏗️ Architecture proposée

### Principe SOLID appliqué

#### 1. Single Responsibility Principle (SRP)

Chaque composant a une responsabilité unique :

- **MonsterStateManager** : Gère uniquement les transitions d'états
- **InvocationApiClient** : Communique uniquement avec l'API d'invocation
- **MonsterRepository** : Gère uniquement la persistance des données
- **AdminService** : Orchestre les workflows admin
- **TransmissionService** : Orchestre le transfert vers l'API d'invocation

#### 2. Open/Closed Principle (OCP)

- Architecture extensible pour ajouter de nouveaux états sans modifier le code existant
- Nouveaux clients API peuvent être ajoutés en implémentant une interface commune

#### 3. Liskov Substitution Principle (LSP)

- Tous les clients API (Gemini, Banana, Invocation) implémentent `BaseClient`
- Tous les repositories peuvent être substitués (utile pour les tests)

#### 4. Interface Segregation Principle (ISP)

- Interfaces minimales et spécialisées
- Les clients n'implémentent que ce dont ils ont besoin

#### 5. Dependency Inversion Principle (DIP)

- Les services dépendent d'abstractions (interfaces), pas d'implémentations concrètes
- Injection de dépendances dans les services

### Principe DRY appliqué

- **Constantes centralisées** : Tous les états dans `MonsterState` (enum)
- **Règles de validation** : Déjà centralisées dans `ValidationRules`
- **Logique de transition** : Une seule méthode `transition()` dans `MonsterStateManager`
- **Mappings API** : Conversion des modèles dans un seul endroit

## 📁 Structure des données

### Base de données (métadonnées)

Nous utiliserons JSON pour simplifier, mais structure prête pour SQLite/PostgreSQL :

```json
{
  "monster_id": "uuid-v4",
  "filename": "pyrolosse.json",
  "state": "PENDING_REVIEW",
  "created_at": "2026-02-08T10:30:00Z",
  "updated_at": "2026-02-08T10:35:00Z",
  "generated_by": "gemini",
  "validated_by": null,
  "validation_date": null,
  "transmitted_at": null,
  "transmission_attempts": 0,
  "last_error": null,
  "history": [
    {
      "from_state": "GENERATED",
      "to_state": "PENDING_REVIEW",
      "timestamp": "2026-02-08T10:30:00Z",
      "actor": "system",
      "note": "Auto transition after generation"
    }
  ],
  "metadata": {
    "image_url": "/static/images/pyrolosse.png",
    "json_path": "/static/jsons/pyrolosse.json"
  }
}
```

### Organisation des fichiers

```
app/static/
├── images/                      # Images générées
├── jsons/
│   ├── generated/              # Monstres générés (état GENERATED)
│   ├── defective/              # Monstres défectueux (état DEFECTIVE)
│   ├── pending_review/         # Monstres en attente (état PENDING_REVIEW)
│   ├── approved/               # Monstres approuvés (état APPROVED)
│   └── transmitted/            # Monstres transmis (état TRANSMITTED)
└── metadata/                   # Métadonnées JSON (historique d'états)
```

## 🔌 Intégration avec l'API Invocation

### Client API Invocation

Nouveau client suivant le pattern des clients existants :

- **Endpoint** : `POST http://localhost:8085/api/invocation/monsters/create`
- **Retry logic** : 3 tentatives avec backoff exponentiel
- **Timeout** : 30 secondes
- **Validation** : Vérification de la réponse

### Mapping des modèles

Transformation de notre modèle vers le modèle de l'API d'invocation :

```python
# Notre modèle
{
  "nom": "Pyrolosse",
  "element": "FIRE",
  "rang": "COMMON",
  "stats": {"hp": 1500, "atk": 250, "def": 180, "vit": 120},
  ...
}

# Modèle API Invocation
{
  "name": "Pyrolosse",
  "element": "FIRE",
  "rank": "COMMON",
  "stats": {"hp": 1500, "atk": 250, "def": 180, "vit": 120},
  ...
}
```

## 🎨 API Admin - Endpoints proposés

### 1. Gestion des états

#### `GET /api/v1/admin/monsters`
Liste tous les monstres avec filtres :
```
Query params:
- state: GENERATED|DEFECTIVE|PENDING_REVIEW|APPROVED|TRANSMITTED|REJECTED
- limit: int (default: 50)
- offset: int (default: 0)
- sort_by: created_at|updated_at|name
- order: asc|desc
```

#### `GET /api/v1/admin/monsters/{monster_id}`
Détails complets d'un monstre (données + métadonnées + historique)

#### `GET /api/v1/admin/monsters/{monster_id}/history`
Historique complet des transitions d'état

### 2. Workflow de validation

#### `POST /api/v1/admin/monsters/{monster_id}/review`
Soumettre une review (approve ou reject) :
```json
{
  "action": "approve|reject",
  "notes": "Raison du rejet ou notes d'approbation",
  "corrected_data": {} // Optionnel si corrections
}
```

#### `POST /api/v1/admin/monsters/{monster_id}/correct`
Corriger un monstre défectueux :
```json
{
  "corrected_data": { /* données corrigées */ }
}
```

### 3. Transmission

#### `POST /api/v1/admin/monsters/{monster_id}/transmit`
Transmettre un monstre approuvé vers l'API d'invocation (manuel)

#### `POST /api/v1/admin/transmit-batch`
Transmettre tous les monstres approuvés en batch

#### `POST /api/v1/admin/transmit-auto`
Activer/désactiver la transmission automatique

### 4. Dashboard & Statistiques

#### `GET /api/v1/admin/dashboard/stats`
Statistiques globales :
```json
{
  "total_monsters": 150,
  "by_state": {
    "GENERATED": 10,
    "PENDING_REVIEW": 25,
    "APPROVED": 30,
    "TRANSMITTED": 80,
    "REJECTED": 5
  },
  "transmission_rate": 0.95,
  "avg_review_time_hours": 2.5
}
```

#### `GET /api/v1/admin/dashboard/recent-activity`
Activité récente (dernières transitions)

### 5. Configuration

#### `GET /api/v1/admin/config`
Configuration actuelle :
```json
{
  "auto_transmit": false,
  "invocation_api_url": "http://localhost:8085",
  "max_retry_attempts": 3
}
```

#### `PUT /api/v1/admin/config`
Mettre à jour la configuration

## 🔒 Sécurité (À implémenter plus tard)

Pour le moment, pas d'authentification, mais architecture prête pour :

- **API Keys** : Pour l'API d'invocation
- **JWT Tokens** : Pour les admins
- **RBAC** : Rôles (admin, reviewer, operator)
- **Audit Log** : Toutes les actions admin sont loggées

## 🚀 Workflow complet

### Scénario 1 : Génération et validation réussies

```
1. POST /api/v1/monsters/generate → Génération du monstre
   État: GENERATED → PENDING_REVIEW (auto)
   
2. GET /api/v1/admin/monsters?state=PENDING_REVIEW → Admin consulte
   
3. GET /api/v1/admin/monsters/{id} → Admin review les détails
   
4. POST /api/v1/admin/monsters/{id}/review → Admin approuve
   État: PENDING_REVIEW → APPROVED
   
5. POST /api/v1/admin/monsters/{id}/transmit → Transmission
   État: APPROVED → TRANSMITTED
   
6. Monstre disponible dans l'API d'invocation ✅
```

### Scénario 2 : Génération avec défaut

```
1. POST /api/v1/monsters/generate → Génération du monstre
   État: DEFECTIVE (validation technique échoue)
   
2. GET /api/v1/admin/monsters?state=DEFECTIVE → Admin consulte
   
3. POST /api/v1/admin/monsters/{id}/correct → Admin corrige
   État: DEFECTIVE → CORRECTED → PENDING_REVIEW
   
4. POST /api/v1/admin/monsters/{id}/review → Admin approuve
   État: PENDING_REVIEW → APPROVED
   
5. POST /api/v1/admin/monsters/{id}/transmit → Transmission
   État: APPROVED → TRANSMITTED
```

### Scénario 3 : Rejet administratif

```
1. POST /api/v1/monsters/generate → Génération du monstre
   État: GENERATED → PENDING_REVIEW
   
2. GET /api/v1/admin/monsters/{id} → Admin review
   
3. POST /api/v1/admin/monsters/{id}/review → Admin rejette
   État: PENDING_REVIEW → REJECTED
   
4. Monstre archivé, ne sera jamais transmis ❌
```

## 📊 Avantages de cette architecture

### ✅ Modularité
- Chaque composant peut être testé indépendamment
- Facile d'ajouter de nouveaux états ou workflows
- Services découplés et réutilisables

### ✅ Traçabilité
- Historique complet de chaque monstre
- Audit trail pour chaque action admin
- Débug facilité en cas de problème

### ✅ Résilience
- Retry automatique en cas d'échec de transmission
- Gestion d'erreurs détaillée
- Rollback possible si nécessaire

### ✅ Evolutivité
- Architecture prête pour une vraie base de données
- Préparé pour l'authentification/autorisation
- Facilement extensible (nouveaux états, nouveaux workflows)

### ✅ Maintenabilité
- Code propre et bien structuré
- Respect des principes SOLID et DRY
- Documentation intégrée

## 🔄 Refactoring nécessaire

### Modifications mineures

1. **FileManager** : Ajouter méthodes pour gérer les différents dossiers d'états
2. **GatchaService** : Intégrer `MonsterStateManager` pour les transitions
3. **Schemas** : Ajouter `MonsterState` enum et schémas de métadonnées

### Nouveaux composants

1. **MonsterStateManager** : Gestion des états et transitions
2. **InvocationApiClient** : Client pour l'API d'invocation
3. **MonsterRepository** : Gestion de la persistance (JSON pour l'instant)
4. **AdminService** : Orchestration des workflows admin
5. **TransmissionService** : Orchestration de la transmission

### Structure finale

```
app/
├── clients/
│   ├── base.py               # BaseClient (existant)
│   ├── gemini.py             # (existant)
│   ├── banana.py             # (existant)
│   ├── minio_client.py       # (existant)
│   └── invocation_api.py     # NOUVEAU
├── repositories/
│   └── monster_repository.py # NOUVEAU
├── services/
│   ├── gatcha_service.py     # MODIFIÉ
│   ├── validation_service.py # (existant)
│   ├── admin_service.py      # NOUVEAU
│   ├── transmission_service.py # NOUVEAU
│   └── state_manager.py      # NOUVEAU
├── schemas/
│   ├── monster.py            # MODIFIÉ (ajout états)
│   ├── metadata.py           # NOUVEAU
│   └── admin.py              # NOUVEAU
└── api/v1/endpoints/
    ├── admin.py              # MODIFIÉ (expansion)
    ├── gatcha.py             # MODIFIÉ (intégration états)
    └── transmission.py        # NOUVEAU (optionnel)
```

## 📝 Notes importantes

1. **Transmission automatique** : non implémentée — la transmission vers `API_invocations` se fait via une action admin explicite (`POST /transmission/transmit/{monster_id}`), pas de scheduler
2. **Validation humaine obligatoire** : Tous les monstres passent par `PENDING_REVIEW`
3. **Idempotence** : Les transmissions sont idempotentes (retry safe)
4. **Async tasks** : Prêt pour intégrer Celery/RQ si nécessaire plus tard
5. **Frontend ready** : API REST complète pour un futur frontend admin

## 🎯 Prochaines étapes

Voir **docs/archive/IMPLEMENTATION_ROADMAP.md** pour le plan d'implémentation historique (déjà réalisé) étape par étape.
