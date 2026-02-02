# Système de Validation des Monstres

## Vue d'ensemble

Ce système valide automatiquement tous les JSONs générés par l'IA avant qu'ils ne soient sauvegardés. Si des anomalies sont détectées, le JSON est stocké dans un dossier séparé avec des métadonnées détaillées, et une interface admin permet à l'administrateur d'examiner et de corriger les données.

## Architecture

### Principes SOLID appliqués

1. **Single Responsibility Principle (SRP)**: Chaque validateur a une responsabilité unique
   - `TypeValidator`: Valide les types de données
   - `EnumValidator`: Valide les énumérations
   - `RangeValidator`: Valide les plages numériques
   - `MonsterStructureValidator`: Valide la structure globale
   - `MonsterEnumValidator`: Valide tous les énums
   - `MonsterRangeValidator`: Valide toutes les plages

2. **Open/Closed Principle (OCP)**: Facile d'ajouter de nouveaux validateurs sans modifier existants

3. **Liskov Substitution Principle (LSP)**: Tous les validateurs suivent le même pattern

4. **Interface Segregation Principle (ISP)**: Interfaces minimales et spécialisées

5. **Dependency Inversion Principle (DIP)**: `MonsterValidationService` dépend d'abstractions

### DRY (Don't Repeat Yourself)

- Toutes les constantes centralisées dans `ValidationRules` (config.py)
- Logique de validation réutilisable et composable
- Pas de duplication de code entre validateurs

### Composants principaux

#### 1. `ValidationRules` (config.py)
Classe centralisée contenant toutes les constantes de validation:
```python
VALID_STATS = {"ATK", "DEF", "HP", "VIT"}
VALID_ELEMENTS = {"FIRE", "WATER", "WIND", "EARTH", "LIGHT", "DARKNESS"}
VALID_RANKS = {"COMMON", "RARE", "EPIC", "LEGENDARY"}

STAT_LIMITS = {
    "hp": (50.0, 1000.0),
    "atk": (10.0, 200.0),
    "def": (10.0, 200.0),
    "vit": (10.0, 150.0),
}

SKILL_LIMITS = {
    "damage": (0.0, 500.0),
    "percent": (0.1, 2.0),
    "cooldown": (0, 5),
}

LVL_MAX = 5.0
MAX_CARD_DESCRIPTION_LENGTH = 200
```

#### 2. `validation_service.py`
Service de validation modulaire:
- `ValidationResult`: Classe conteneur pour les résultats
- `ValidationError`: Classe représentant une erreur unique
- `TypeValidator`: Valide les types de données
- `EnumValidator`: Valide les énumérations
- `RangeValidator`: Valide les plages numériques
- `MonsterStructureValidator`: Valide la structure
- `MonsterEnumValidator`: Valide les énums
- `MonsterRangeValidator`: Valide les plages
- `MonsterValidationService`: Orchestre les validateurs (Pattern Facade)

#### 3. `FileManager` amélioré (utils/file_manager.py)
Gestion des JSONs défectueux:
- `save_json()`: Sauvegarde valide (ancienne méthode)
- `save_defective_json()`: Sauvegarde avec métadonnées
- `get_defective_json()`: Récupère un JSON défectueux
- `list_defective_jsons()`: Liste tous les défectueux
- `move_defective_to_valid()`: Déplace vers dossier valide après correction
- `update_defective_json()`: Mise à jour avec corrections
- `delete_defective_json()`: Supprime après rejet

#### 4. `GatchaService` améliorisé (services/gatcha_service.py)
Intégration de la validation:
- Valide avant génération d'image
- Sauvegarde les JSONs défectueux avec métadonnées
- Génère quand même l'image (pour examen)
- Retourne le statut de validation au client

#### 5. Endpoints Admin (api/v1/endpoints/admin.py)
Interface pour l'administration:
- `GET /api/v1/admin/defective`: Liste les JSONs défectueux
- `GET /api/v1/admin/defective/{filename}`: Détail d'un JSON défectueux
- `POST /api/v1/admin/defective/{filename}/approve`: Approuver et corriger
- `POST /api/v1/admin/defective/{filename}/reject`: Rejeter et supprimer
- `PUT /api/v1/admin/defective/{filename}/update`: Mettre à jour les corrections
- `POST /api/v1/admin/defective/{filename}/validate`: Valider sans approuver
- `GET /api/v1/admin/validation-rules`: Récupérer les règles de validation

## Flux de validation

### Création d'un monstre

```
1. Utilisateur → POST /api/v1/monsters/create
2. GatchaService.create_monster()
3. GeminiClient.generate_monster_profile() → JSON
4. GatchaService._process_monster_asset()
   ├─ MonsterValidationService.validate()
   │  ├─ MonsterStructureValidator.validate_structure()
   │  ├─ MonsterEnumValidator.validate_enums()
   │  └─ MonsterRangeValidator.validate_ranges()
   │
   └─ Si valide:
      ├─ BananaClient.generate_pixel_art()
      ├─ FileManager.save_json()
      └─ Retour: JSON PATH valide
      
   └─ Si invalide:
      ├─ BananaClient.generate_pixel_art()
      ├─ FileManager.save_defective_json()
      ├─ Log erreurs
      └─ Retour: JSON PATH défectueux + erreurs
```

### Correction d'un monstre défectueux

```
1. Admin → GET /api/v1/admin/defective
2. Voir liste des défectueux
3. GET /api/v1/admin/defective/{filename}
4. Voir détails + erreurs
5. Admin corrige les données localement
6. POST /api/v1/admin/defective/{filename}/approve
   ├─ Validation du JSON corrigé
   ├─ Si valide:
   │  ├─ FileManager.move_defective_to_valid()
   │  └─ Retour: succès
   └─ Si invalide:
      └─ Retour: erreurs persistantes
```

## Dossier de stockage

```
app/static/
├── jsons/              # JSONs valides sauvegardés
│   ├── dragon.json
│   ├── phoenix.json
│   └── ...
├── jsons_defective/    # JSONs défectueux en attente de révision
│   ├── baddragon_20250202_143022.json
│   ├── phoenix_20250202_120030.json
│   └── ...
└── images/
    ├── dragon.png
    ├── phoenix.png
    └── ...
```

### Structure d'un JSON défectueux

```json
{
  "created_at": "2025-02-02T14:30:22.123456",
  "updated_at": "2025-02-02T14:35:00.654321",
  "status": "pending_review",
  "monster_data": {
    "nom": "BadDragon",
    "element": "INVALID_ELEMENT",
    ...
  },
  "validation_errors": [
    {
      "field": "element",
      "error_type": "enum_invalid",
      "message": "Invalid value 'INVALID_ELEMENT'. Allowed: {'FIRE', 'WATER', ...}"
    },
    {
      "field": "stats.hp",
      "error_type": "value_out_of_range",
      "message": "Value 2000 out of range [50.0, 1000.0]"
    }
  ],
  "notes": "Admin notes for later reference"
}
```

## Exemples d'utilisation

### Créer un monstre

```bash
curl -X POST http://localhost:8000/api/v1/monsters/create \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Cyberpunk Dragon"}'
```

Réponse:
```json
{
  "nom": "Cyber Dragon",
  "element": "FIRE",
  "rang": "RARE",
  "stats": {...},
  "description_carte": "...",
  "description_visuelle": "...",
  "skills": [...],
  "image_path": "...",
  "json_path": "/static/jsons/cyberdragon.json",
  "_is_valid": true
}
```

### Lister les JSONs défectueux

```bash
curl http://localhost:8000/api/v1/admin/defective
```

Réponse:
```json
[
  {
    "filename": "baddragon_20250202_143022.json",
    "created_at": "2025-02-02T14:30:22.123456",
    "status": "pending_review",
    "error_count": 2,
    "monster_name": "BadDragon"
  }
]
```

### Voir les détails d'un JSON défectueux

```bash
curl http://localhost:8000/api/v1/admin/defective/baddragon_20250202_143022.json
```

### Approuver après correction

```bash
curl -X POST http://localhost:8000/api/v1/admin/defective/baddragon_20250202_143022.json/approve \
  -H "Content-Type: application/json" \
  -d '{
    "corrected_data": {
      "nom": "CyberDragon",
      "element": "FIRE",
      ...
    },
    "notes": "Fixed element and stats"
  }'
```

### Récupérer les règles de validation

```bash
curl http://localhost:8000/api/v1/admin/validation-rules
```

## Gestion des erreurs

Les types d'erreurs de validation:

1. **missing_field**: Champ requis manquant
2. **type_mismatch**: Type de données incorrect
3. **enum_invalid**: Valeur non valide pour une énumération
4. **value_out_of_range**: Valeur numérique hors limites

## Étendre le système

Pour ajouter une nouvelle règle de validation:

1. Ajouter la constante dans `ValidationRules` (config.py)
2. Créer ou modifier un validateur dans `validation_service.py`
3. Intégrer dans `MonsterValidationService.validate()` si nécessaire
4. Tester avec des cas d'erreur

Exemple: Ajouter une validation de longueur de description

```python
# 1. Dans ValidationRules:
MAX_DESCRIPTION_LENGTH = 500

# 2. Dans MonsterRangeValidator:
if "description_visuelle" in monster_data:
    desc = monster_data["description_visuelle"]
    if len(desc) > ValidationRules.MAX_DESCRIPTION_LENGTH:
        result.add_error(
            "description_visuelle",
            "value_out_of_range",
            f"Description too long..."
        )
```

## Avantages de cette architecture

✅ **Modulaire**: Chaque validateur est indépendant  
✅ **Testable**: Facile à tester unitairement  
✅ **Extensible**: Ajouter des validateurs sans modification  
✅ **Maintenable**: Constantes centralisées, DRY  
✅ **SOLID**: Suit tous les principes SOLID  
✅ **Utilisateur-friendly**: Admin peut corriger les erreurs  
✅ **Traçable**: Historique des erreurs et corrections  
✅ **Sûr**: Validation stricte avant intégration  

## Futures améliorations

- [ ] Intégration avec une base de données pour l'historique
- [ ] Notifications email pour l'admin
- [ ] Interface web de gestion
- [ ] Règles de validation personnalisables par rang
- [ ] Validation des noms uniques
- [ ] Support multi-langues pour les messages d'erreur
