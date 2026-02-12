# Système de gestion multi-images pour les monstres

## Vue d'ensemble

Un système complet de gestion d'images multiples pour les monstres a été mis en place. Il permet de :
- Stocker plusieurs images par monstre
- Désigner une image par défaut
- Générer de nouvelles images avec des prompts personnalisés

## Architecture

### 1. Base de données

**Nouvelle table : `monster_images`**
- `id` : Identifiant unique de l'image
- `monster_id` : Référence au monstre (clé étrangère vers `monsters.id`)
- `image_name` : Nom de l'image
- `image_url` : URL complète de l'image sur MinIO
- `prompt` : Prompt utilisé pour générer l'image
- `is_default` : Booléen indiquant si c'est l'image par défaut
- `created_at` : Date de création

**Migration Alembic** : `20260212_1939-97343a9146db_add_monster_images_table.py`

### 2. Modèles

**Fichier** : [app/models/monster_image_model.py](app/models/monster_image_model.py)
- Classe `MonsterImage` : Modèle SQLAlchemy pour la table
- Relation avec `Monster` via `monster.images`

**Modification** : [app/models/monster_model.py](app/models/monster_model.py)
- Ajout de la relation `images` dans le modèle `Monster`

### 3. Schémas Pydantic

**Fichier** : [app/schemas/image.py](app/schemas/image.py)

- `MonsterImageBase` : Schéma de base
- `MonsterImageCreate` : Création d'une nouvelle image (requête API)
- `MonsterImageResponse` : Réponse API avec toutes les métadonnées
- `MonsterImageListResponse` : Liste des images d'un monstre
- `SetDefaultImageRequest` : Définir l'image par défaut

### 4. Repository

**Fichier** : [app/repositories/monster_image_repository.py](app/repositories/monster_image_repository.py)

Méthodes principales :
- `create_image()` : Crée une nouvelle image
- `get_images_by_monster_id()` : Récupère toutes les images d'un monstre
- `get_default_image()` : Récupère l'image par défaut
- `set_default_image()` : Définit une image comme défaut
- `delete_image()` : Supprime une image

### 5. Service

**Fichier** : [app/services/image_service.py](app/services/image_service.py)

Méthodes principales :
- `create_default_image_for_monster()` : Crée l'image par défaut lors de la génération
- `create_custom_image_for_monster()` : Génère une nouvelle image personnalisée
- `get_monster_images()` : Récupère toutes les images
- `set_default_image()` : Change l'image par défaut

### 6. Intégration automatique

**Fichier** : [app/services/gatcha_service.py](app/services/gatcha_service.py)

Lors de la génération d'un monstre, le service crée automatiquement une entrée dans `monster_images` avec :
- Le nom du monstre comme `image_name`
- L'URL de l'image générée
- Le prompt complet utilisé
- `is_default = True`

## Routes API

**Préfixe** : `/api/v1/monsters/images`

### 1. Générer une nouvelle image

```http
POST /api/v1/monsters/images/generate
```

**Body** :
```json
{
  "monster_id": "uuid-du-monstre",
  "image_name": "nom_de_la_nouvelle_image",
  "custom_prompt": "Description visuelle personnalisée"
}
```

**Note** : Le `custom_prompt` sera automatiquement injecté dans `IMAGE_GENERATION` du fichier [prompts.py](app/core/prompts.py).

**Réponse** :
```json
{
  "id": 1,
  "monster_id": 123,
  "image_name": "nom_de_la_nouvelle_image",
  "image_url": "https://minio.../image.webp",
  "prompt": "Full body illustration of ...",
  "is_default": false,
  "created_at": "2026-02-12T19:47:00Z"
}
```

### 2. Récupérer toutes les images d'un monstre

```http
GET /api/v1/monsters/images/{monster_id}
```

**Réponse** :
```json
{
  "monster_id": "uuid-du-monstre",
  "monster_name": "Nom du Monstre",
  "images": [
    {
      "id": 1,
      "monster_id": 123,
      "image_name": "nom_monstre_default",
      "image_url": "https://minio.../image.webp",
      "prompt": "...",
      "is_default": true,
      "created_at": "2026-02-12T19:00:00Z"
    },
    {
      "id": 2,
      "monster_id": 123,
      "image_name": "nom_monstre_variant",
      "image_url": "https://minio.../image2.webp",
      "prompt": "...",
      "is_default": false,
      "created_at": "2026-02-12T19:30:00Z"
    }
  ],
  "default_image": {
    "id": 1,
    ...
  }
}
```

### 3. Définir l'image par défaut

```http
PUT /api/v1/monsters/images/{monster_id}/default
```

**Body** :
```json
{
  "image_id": 2
}
```

**Réponse** : L'image mise à jour avec `is_default: true`

## Workflow complet

### 1. Création automatique d'un monstre
Lorsqu'un monstre est créé (via `/api/v1/monsters/`), le système :
1. Génère le JSON du monstre
2. Génère l'image via `BananaClient`
3. Upload l'image sur MinIO
4. Sauvegarde le monstre dans `monsters`
5. **NOUVEAU** : Crée automatiquement une entrée dans `monster_images` avec `is_default=True`

### 2. Génération d'une image personnalisée
1. Admin appelle `POST /api/v1/monsters/images/generate`
2. Le service récupère le monstre
3. Génère une nouvelle image avec le prompt personnalisé
4. Upload sur MinIO
5. Crée une entrée dans `monster_images` avec `is_default=False`

### 3. Changement d'image par défaut
1. Admin appelle `PUT /api/v1/monsters/images/{monster_id}/default`
2. Le repository retire le flag `is_default` de toutes les autres images
3. Définit la nouvelle image comme défaut

## Notes techniques

### Gestion du prompt
Le prompt personnalisé est **toujours injecté** dans le template `IMAGE_GENERATION` :
```python
full_prompt = GatchaPrompts.IMAGE_GENERATION.format(prompt=custom_prompt)
```

Exemple :
```
custom_prompt = "A fierce dragon with blue scales"
→ "Full body illustration of A fierce dragon with blue scales, set in a detailed..."
```

### Contraintes de la base de données
- Suppression en cascade : Si un monstre est supprimé, toutes ses images sont automatiquement supprimées
- Un seul `is_default=True` par monstre (géré par le repository)

### Compatibilité
Le système est rétrocompatible :
- Les monstres existants continuent de fonctionner
- Leur champ `image_path` reste utilisé
- La migration vers `monster_images` peut se faire progressivement

## Tests recommandés

1. **Créer un nouveau monstre** : Vérifier qu'une entrée est créée dans `monster_images`
2. **Générer une image personnalisée** : Tester avec différents prompts
3. **Lister les images** : Vérifier que toutes les images apparaissent
4. **Changer l'image par défaut** : Vérifier que seule une image a `is_default=True`
5. **Supprimer un monstre** : Vérifier que ses images sont supprimées en cascade

## Documentation API

La documentation interactive Swagger est disponible à : `http://localhost:8000/docs`

Les nouvelles routes apparaissent dans la section **Monster Images**.
