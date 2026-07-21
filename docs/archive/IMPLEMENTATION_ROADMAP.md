# Roadmap d'Implémentation - Système de Gestion du Cycle de Vie

## 🎯 Vue d'ensemble

Cette roadmap détaille l'implémentation du système de gestion du cycle de vie des monstres, de la génération à la transmission vers l'API d'invocation, en passant par la validation administrative.

## 📊 Phases d'implémentation

### Phase 1 : Fondations (2-3h)
### Phase 2 : Gestion des états (3-4h)
### Phase 3 : API Admin complète (4-5h)
### Phase 4 : Transmission vers API Invocation (2-3h)
### Phase 5 : Refactoring et optimisation (2-3h)
### Phase 6 : Tests et documentation (2-3h)

**Durée totale estimée : 15-21 heures**

---

## 📋 Phase 1 : Fondations (2-3h)

### Objectif
Mettre en place les bases du nouveau système sans casser l'existant.

### 1.1 Créer les énumérations et schémas de base

**Fichier : `app/schemas/monster.py`**

```python
# Ajouter en haut du fichier
from enum import Enum

class MonsterState(str, Enum):
    """États possibles d'un monstre dans son cycle de vie"""
    GENERATED = "GENERATED"
    DEFECTIVE = "DEFECTIVE"
    CORRECTED = "CORRECTED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    TRANSMITTED = "TRANSMITTED"
    REJECTED = "REJECTED"

class TransitionAction(str, Enum):
    """Actions possibles pour les transitions"""
    APPROVE = "approve"
    REJECT = "reject"
    CORRECT = "correct"
    TRANSMIT = "transmit"
```

**✅ Tests :**
- Vérifier que les enums sont importables
- Vérifier la validation Pydantic

### 1.2 Créer les schémas de métadonnées

**Fichier : `app/schemas/metadata.py` (nouveau)**

Copier le contenu depuis `TECHNICAL_SPECIFICATIONS.md` section "Métadonnées des monstres".

**✅ Tests :**
- Instancier `MonsterMetadata` avec des données valides
- Vérifier la sérialisation JSON

### 1.3 Créer les schémas admin

**Fichier : `app/schemas/admin.py` (nouveau)**

Copier le contenu depuis `TECHNICAL_SPECIFICATIONS.md` section "Schémas Admin".

**✅ Tests :**
- Valider tous les schémas avec des données de test
- Vérifier les contraintes (patterns, ranges)

### 1.4 Mettre à jour la configuration

**Fichier : `app/core/config.py`**

```python
class Settings(BaseSettings):
    # ... (existant)
    
    # API Invocation
    INVOCATION_API_URL: str = "http://localhost:8085"
    INVOCATION_API_TIMEOUT: int = 30
    INVOCATION_API_MAX_RETRIES: int = 3
    INVOCATION_API_RETRY_DELAY: int = 2
    
    # Transmission automatique
    AUTO_TRANSMIT_ENABLED: bool = False
    AUTO_TRANSMIT_INTERVAL_SECONDS: int = 300
    
    # Chemins
    MONSTERS_BASE_PATH: str = "app/static"
    METADATA_DIR: str = "app/static/metadata"
```

**✅ Tests :**
- Charger la config avec `get_settings()`
- Vérifier les valeurs par défaut

### 1.5 Créer la structure de dossiers

**Script de migration : `scripts/setup_directories.py` (nouveau)**

```python
from pathlib import Path

def setup_directories():
    base = Path("app/static")
    
    dirs = [
        base / "metadata",
        base / "jsons" / "generated",
        base / "jsons" / "defective",  # Renommer depuis jsons_defective
        base / "jsons" / "corrected",
        base / "jsons" / "pending_review",
        base / "jsons" / "approved",
        base / "jsons" / "transmitted",
        base / "jsons" / "rejected",
    ]
    
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {dir_path}")

if __name__ == "__main__":
    setup_directories()
```

**✅ Exécution :**
```bash
python scripts/setup_directories.py
```

### 1.6 Migrer les JSONs existants

**Script de migration : `scripts/migrate_existing_monsters.py` (nouveau)**

```python
import json
import uuid
from pathlib import Path
from datetime import datetime
from app.schemas.metadata import MonsterMetadata
from app.core.constants import MonsterState

def migrate_existing_monsters():
    """Migre les monstres existants vers le nouveau système"""
    
    # Monstres valides
    valid_jsons = Path("app/static/jsons")
    valid_files = [f for f in valid_jsons.glob("*.json") if f.is_file()]
    
    for json_file in valid_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                monster_data = json.load(f)
            
            # Créer les métadonnées
            monster_id = str(uuid.uuid4())
            metadata = MonsterMetadata(
                monster_id=monster_id,
                filename=json_file.name,
                state=MonsterState.TRANSMITTED,  # Considérés comme déjà transmis
                created_at=datetime.fromtimestamp(json_file.stat().st_ctime),
                updated_at=datetime.fromtimestamp(json_file.stat().st_mtime),
                generated_by="gemini",
                is_valid=True,
                transmitted_at=datetime.utcnow(),
            )
            
            # Sauvegarder les métadonnées
            metadata_path = Path("app/static/metadata") / f"{monster_id}_metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata.model_dump(mode='json'), f, indent=2, ensure_ascii=False)
            
            # Déplacer le fichier
            new_path = Path("app/static/jsons/transmitted") / json_file.name
            json_file.rename(new_path)
            
            print(f"✓ Migrated: {json_file.name} → {new_path}")
            
        except Exception as e:
            print(f"✗ Failed to migrate {json_file.name}: {e}")
    
    # Monstres défectueux
    defective_dir = Path("app/static/jsons_defective")
    if defective_dir.exists():
        defective_files = list(defective_dir.glob("*.json"))
        
        for json_file in defective_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                monster_data = data.get("monster_data", {})
                validation_errors = data.get("validation_errors", [])
                
                # Créer les métadonnées
                monster_id = str(uuid.uuid4())
                metadata = MonsterMetadata(
                    monster_id=monster_id,
                    filename=json_file.name,
                    state=MonsterState.DEFECTIVE,
                    created_at=datetime.fromtimestamp(json_file.stat().st_ctime),
                    updated_at=datetime.fromtimestamp(json_file.stat().st_mtime),
                    generated_by="gemini",
                    is_valid=False,
                    validation_errors=validation_errors,
                )
                
                # Sauvegarder les métadonnées
                metadata_path = Path("app/static/metadata") / f"{monster_id}_metadata.json"
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata.model_dump(mode='json'), f, indent=2, ensure_ascii=False)
                
                # Déplacer le fichier (garder juste monster_data)
                new_path = Path("app/static/jsons/defective") / json_file.name
                with open(new_path, 'w', encoding='utf-8') as f:
                    json.dump(monster_data, f, indent=2, ensure_ascii=False)
                
                json_file.unlink()  # Supprimer l'ancien
                
                print(f"✓ Migrated defective: {json_file.name} → {new_path}")
                
            except Exception as e:
                print(f"✗ Failed to migrate defective {json_file.name}: {e}")

if __name__ == "__main__":
    migrate_existing_monsters()
```

**✅ Exécution :**
```bash
python scripts/migrate_existing_monsters.py
```

**⚠️ Attention :** Faire un backup avant la migration !

---

## 📋 Phase 2 : Gestion des états (3-4h)

### Objectif
Implémenter la logique de gestion des états et des transitions.

### 2.1 Créer le StateManager

**Fichier : `app/services/state_manager.py` (nouveau)**

Copier le contenu depuis `TECHNICAL_SPECIFICATIONS.md` section "MonsterStateManager".

**✅ Tests unitaires :**
```python
# tests/test_state_manager.py
def test_valid_transition():
    manager = MonsterStateManager()
    assert manager.can_transition(
        MonsterState.GENERATED, 
        MonsterState.PENDING_REVIEW
    )

def test_invalid_transition():
    manager = MonsterStateManager()
    assert not manager.can_transition(
        MonsterState.TRANSMITTED, 
        MonsterState.PENDING_REVIEW
    )

def test_transition_updates_metadata():
    manager = MonsterStateManager()
    metadata = MonsterMetadata(...)
    updated = manager.transition(
        metadata, 
        MonsterState.PENDING_REVIEW,
        actor="system"
    )
    assert updated.state == MonsterState.PENDING_REVIEW
    assert len(updated.history) == 1
```

### 2.2 Créer le Repository

**Fichier : `app/repositories/monster_repository.py` (nouveau)**

Copier le contenu depuis `TECHNICAL_SPECIFICATIONS.md` section "MonsterRepository".

**✅ Tests unitaires :**
```python
# tests/test_monster_repository.py
def test_save_and_get():
    repo = MonsterRepository()
    metadata = create_test_metadata()
    monster_data = create_test_monster()
    
    assert repo.save(metadata, monster_data)
    
    result = repo.get(metadata.monster_id)
    assert result is not None
    assert result.metadata.monster_id == metadata.monster_id

def test_list_by_state():
    repo = MonsterRepository()
    results = repo.list_by_state(MonsterState.PENDING_REVIEW, limit=10)
    assert isinstance(results, list)

def test_move_to_state():
    repo = MonsterRepository()
    # ... test du déplacement de fichier
```

### 2.3 Refactorer GatchaService

**Fichier : `app/services/gatcha_service.py`**

Modifications à apporter :

```python
from app.services.state_manager import MonsterStateManager
from app.repositories.monster_repository import MonsterRepository
import uuid

class GatchaService:
    def __init__(self):
        self.gemini_client = GeminiClient()
        self.banana_client = BananaClient()
        self.file_manager = FileManager()
        self.validation_service = MonsterValidationService()
        self.state_manager = MonsterStateManager()  # NOUVEAU
        self.repository = MonsterRepository()        # NOUVEAU

    async def _process_monster_asset(
        self, monster_data: Dict[str, Any], fallback_prompt: str
    ) -> MonsterResponse:
        """Modification pour intégrer la gestion d'états"""
        
        monster_name = monster_data.get("nom", "unknown_monster")
        filename_base = self._get_filename_base(monster_data)
        
        # Générer un ID unique
        monster_id = str(uuid.uuid4())
        
        # Validation
        validation_result = self.validation_service.validate(monster_data)
        
        # Générer l'image
        image_url = await self._generate_image(
            monster_data, fallback_prompt, filename_base
        )
        
        # Créer les métadonnées
        from datetime import datetime
        from app.schemas.metadata import MonsterMetadata, StateTransition
        
        initial_state = (
            MonsterState.DEFECTIVE if not validation_result.is_valid 
            else MonsterState.GENERATED
        )
        
        metadata = MonsterMetadata(
            monster_id=monster_id,
            filename=f"{filename_base}.json",
            state=initial_state,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            generated_by="gemini",
            generation_prompt=fallback_prompt,
            is_valid=validation_result.is_valid,
            validation_errors=(
                [e.model_dump() for e in validation_result.errors] 
                if not validation_result.is_valid else None
            ),
            metadata={
                "image_url": image_url,
                "json_path": f"/static/jsons/{initial_state.value.lower()}/{filename_base}.json"
            },
            history=[
                StateTransition(
                    from_state=None,
                    to_state=initial_state,
                    timestamp=datetime.utcnow(),
                    actor="system",
                    note="Initial generation"
                )
            ]
        )
        
        # Ajouter l'URL de l'image aux données du monstre
        monster_data["image_url"] = image_url
        
        # Sauvegarder avec le repository
        self.repository.save(metadata, monster_data)
        
        # Transition automatique vers PENDING_REVIEW si valide
        if validation_result.is_valid:
            metadata = self.state_manager.transition(
                metadata,
                MonsterState.PENDING_REVIEW,
                actor="system",
                note="Auto-transition after successful generation"
            )
            self.repository.save(metadata, monster_data)
            self.repository.move_to_state(monster_id, MonsterState.PENDING_REVIEW)
        
        # Retourner la réponse
        return MonsterResponse(
            **monster_data,
            image_path=image_url,
            json_path=metadata.metadata.get("json_path"),
        )
```

**✅ Tests d'intégration :**
- Générer un monstre valide → doit être en PENDING_REVIEW
- Générer un monstre défectueux → doit être en DEFECTIVE

---

## 📋 Phase 3 : API Admin complète (4-5h)

### Objectif
Créer toutes les routes admin pour gérer les monstres.

### 3.1 Créer le AdminService

**Fichier : `app/services/admin_service.py` (nouveau)**

```python
from typing import List, Optional, Dict, Any
from app.repositories.monster_repository import MonsterRepository
from app.services.state_manager import MonsterStateManager
from app.services.validation_service import MonsterValidationService
from app.schemas.metadata import MonsterMetadata, MonsterWithMetadata
from app.core.constants import MonsterState, TransitionAction
from app.schemas.admin import (
    MonsterSummary, MonsterDetail, DashboardStats
)
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AdminService:
    """Service d'administration des monstres"""
    
    def __init__(self):
        self.repository = MonsterRepository()
        self.state_manager = MonsterStateManager()
        self.validation_service = MonsterValidationService()
    
    def list_monsters(
        self,
        state: Optional[MonsterState] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "created_at",
        order: str = "desc"
    ) -> List[MonsterSummary]:
        """Liste les monstres avec filtres"""
        
        if state:
            metadata_list = self.repository.list_by_state(state, limit, offset)
        else:
            metadata_list = self.repository.list_all(limit, offset)
        
        summaries = []
        for metadata in metadata_list:
            monster = self.repository.get(metadata.monster_id)
            if monster:
                summaries.append(MonsterSummary(
                    monster_id=metadata.monster_id,
                    filename=metadata.filename,
                    name=monster.monster_data.get("nom", "Unknown"),
                    element=monster.monster_data.get("element", "Unknown"),
                    rank=monster.monster_data.get("rang", "Unknown"),
                    state=metadata.state,
                    created_at=metadata.created_at,
                    updated_at=metadata.updated_at,
                    is_valid=metadata.is_valid,
                    review_notes=metadata.review_notes,
                ))
        
        return summaries
    
    def get_monster_detail(self, monster_id: str) -> Optional[MonsterDetail]:
        """Récupère les détails complets d'un monstre"""
        
        monster = self.repository.get(monster_id)
        if not monster:
            return None
        
        # Construire l'URL de l'image
        image_url = monster.metadata.metadata.get("image_url", "")
        
        # Validation report si erreurs
        validation_report = None
        if not monster.metadata.is_valid and monster.metadata.validation_errors:
            validation_report = {
                "is_valid": False,
                "errors": monster.metadata.validation_errors
            }
        
        return MonsterDetail(
            metadata=monster.metadata,
            monster_data=monster.monster_data,
            image_url=image_url,
            validation_report=validation_report
        )
    
    def review_monster(
        self,
        monster_id: str,
        action: TransitionAction,
        notes: Optional[str] = None,
        corrected_data: Optional[Dict[str, Any]] = None,
        admin_name: str = "admin"
    ) -> MonsterMetadata:
        """Review un monstre (approve ou reject)"""
        
        monster = self.repository.get(monster_id)
        if not monster:
            raise ValueError(f"Monster {monster_id} not found")
        
        # Vérifier l'état actuel
        if monster.metadata.state != MonsterState.PENDING_REVIEW:
            raise ValueError(
                f"Monster must be in PENDING_REVIEW state, current: {monster.metadata.state}"
            )
        
        # Déterminer l'état cible
        if action == TransitionAction.APPROVE:
            target_state = MonsterState.APPROVED
        elif action == TransitionAction.REJECT:
            target_state = MonsterState.REJECTED
        else:
            raise ValueError(f"Invalid action: {action}")
        
        # Si corrected_data fourni, valider et mettre à jour
        if corrected_data:
            validation_result = self.validation_service.validate(corrected_data)
            if not validation_result.is_valid:
                raise ValueError(
                    "Corrected data is invalid", 
                    validation_result.to_dict()
                )
            monster.monster_data = corrected_data
        
        # Mettre à jour les métadonnées
        monster.metadata.reviewed_by = admin_name
        monster.metadata.review_date = datetime.utcnow()
        monster.metadata.review_notes = notes
        
        # Transition d'état
        metadata = self.state_manager.transition(
            monster.metadata,
            target_state,
            actor=admin_name,
            note=notes or f"Review: {action.value}"
        )
        
        # Sauvegarder
        self.repository.save(metadata, monster.monster_data)
        self.repository.move_to_state(monster_id, target_state)
        
        logger.info(f"Monster {monster_id} reviewed: {action.value} by {admin_name}")
        
        return metadata
    
    def correct_defective(
        self,
        monster_id: str,
        corrected_data: Dict[str, Any],
        notes: Optional[str] = None,
        admin_name: str = "admin"
    ) -> MonsterMetadata:
        """Corrige un monstre défectueux"""
        
        monster = self.repository.get(monster_id)
        if not monster:
            raise ValueError(f"Monster {monster_id} not found")
        
        if monster.metadata.state != MonsterState.DEFECTIVE:
            raise ValueError(
                f"Monster must be in DEFECTIVE state, current: {monster.metadata.state}"
            )
        
        # Valider les données corrigées
        validation_result = self.validation_service.validate(corrected_data)
        if not validation_result.is_valid:
            raise ValueError(
                "Corrected data is still invalid",
                validation_result.to_dict()
            )
        
        # Mettre à jour les données
        monster.monster_data = corrected_data
        monster.metadata.is_valid = True
        monster.metadata.validation_errors = None
        
        # Transition DEFECTIVE → CORRECTED → PENDING_REVIEW
        metadata = self.state_manager.transition(
            monster.metadata,
            MonsterState.CORRECTED,
            actor=admin_name,
            note=notes or "Corrected by admin"
        )
        
        self.repository.save(metadata, monster.monster_data)
        self.repository.move_to_state(monster_id, MonsterState.CORRECTED)
        
        # Auto-transition vers PENDING_REVIEW
        metadata = self.state_manager.transition(
            metadata,
            MonsterState.PENDING_REVIEW,
            actor="system",
            note="Auto-transition after correction"
        )
        
        self.repository.save(metadata, monster.monster_data)
        self.repository.move_to_state(monster_id, MonsterState.PENDING_REVIEW)
        
        logger.info(f"Monster {monster_id} corrected by {admin_name}")
        
        return metadata
    
    def get_dashboard_stats(self) -> DashboardStats:
        """Récupère les statistiques du dashboard"""
        
        # Compter par état
        counts = self.repository.count_by_state()
        
        total = sum(counts.values())
        transmitted = counts.get(MonsterState.TRANSMITTED, 0)
        transmission_rate = transmitted / total if total > 0 else 0.0
        
        # Activité récente (dernières transitions)
        recent_activity = []
        all_metadata = self.repository.list_all(limit=20)
        
        for metadata in all_metadata:
            if metadata.history:
                last_transition = metadata.history[-1]
                recent_activity.append({
                    "monster_id": metadata.monster_id,
                    "monster_name": metadata.filename.replace(".json", ""),
                    "transition": f"{last_transition.from_state} → {last_transition.to_state}",
                    "timestamp": last_transition.timestamp,
                    "actor": last_transition.actor,
                })
        
        # Calculer le temps moyen de review
        avg_review_time = None
        review_times = []
        
        for metadata in all_metadata:
            if metadata.review_date and metadata.created_at:
                delta = metadata.review_date - metadata.created_at
                review_times.append(delta.total_seconds() / 3600)  # heures
        
        if review_times:
            avg_review_time = sum(review_times) / len(review_times)
        
        return DashboardStats(
            total_monsters=total,
            by_state=counts,
            transmission_rate=transmission_rate,
            avg_review_time_hours=avg_review_time,
            recent_activity=recent_activity[:10]
        )
```

### 3.2 Refactorer les endpoints admin

**Fichier : `app/api/v1/endpoints/admin.py`**

Remplacer / compléter avec :

```python
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from app.services.admin_service import AdminService
from app.schemas.admin import (
    MonsterListFilter, MonsterSummary, MonsterDetail,
    ReviewRequest, CorrectionRequest, DashboardStats
)
from app.core.constants import MonsterState
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

def get_admin_service() -> AdminService:
    """Dependency injection"""
    return AdminService()

@router.get("/monsters", response_model=List[MonsterSummary])
async def list_monsters(
    state: Optional[MonsterState] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    service: AdminService = Depends(get_admin_service)
):
    """
    Liste tous les monstres avec filtres optionnels.
    
    - **state**: Filtrer par état (optionnel)
    - **limit**: Nombre max de résultats (1-200)
    - **offset**: Pagination
    - **sort_by**: Champ de tri
    - **order**: Ordre (asc|desc)
    """
    try:
        return service.list_monsters(state, limit, offset, sort_by, order)
    except Exception as e:
        logger.error(f"Error listing monsters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monsters/{monster_id}", response_model=MonsterDetail)
async def get_monster_detail(
    monster_id: str,
    service: AdminService = Depends(get_admin_service)
):
    """
    Récupère les détails complets d'un monstre.
    
    Inclut :
    - Métadonnées complètes
    - Données du monstre
    - Historique des transitions
    - Rapport de validation si erreurs
    """
    try:
        detail = service.get_monster_detail(monster_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Monster not found")
        return detail
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting monster {monster_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monsters/{monster_id}/history")
async def get_monster_history(
    monster_id: str,
    service: AdminService = Depends(get_admin_service)
):
    """Récupère l'historique complet des transitions d'un monstre"""
    try:
        monster = service.repository.get(monster_id)
        if not monster:
            raise HTTPException(status_code=404, detail="Monster not found")
        
        return {
            "monster_id": monster_id,
            "current_state": monster.metadata.state,
            "history": [
                {
                    "from_state": t.from_state,
                    "to_state": t.to_state,
                    "timestamp": t.timestamp,
                    "actor": t.actor,
                    "note": t.note,
                }
                for t in monster.metadata.history
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting history for {monster_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monsters/{monster_id}/review")
async def review_monster(
    monster_id: str,
    request: ReviewRequest,
    service: AdminService = Depends(get_admin_service)
):
    """
    Review un monstre (approve ou reject).
    
    - **action**: "approve" ou "reject"
    - **notes**: Notes optionnelles
    - **corrected_data**: Données corrigées si nécessaire
    """
    try:
        metadata = service.review_monster(
            monster_id,
            request.action,
            request.notes,
            request.corrected_data,
            admin_name="admin"  # TODO: Récupérer depuis auth
        )
        
        return {
            "status": "success",
            "monster_id": monster_id,
            "new_state": metadata.state,
            "message": f"Monster {request.action.value}d successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error reviewing monster {monster_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monsters/{monster_id}/correct")
async def correct_defective_monster(
    monster_id: str,
    request: CorrectionRequest,
    service: AdminService = Depends(get_admin_service)
):
    """
    Corrige un monstre défectueux.
    
    Le monstre doit être en état DEFECTIVE.
    Après correction, il passe en PENDING_REVIEW.
    """
    try:
        metadata = service.correct_defective(
            monster_id,
            request.corrected_data,
            request.notes,
            admin_name="admin"
        )
        
        return {
            "status": "success",
            "monster_id": monster_id,
            "new_state": metadata.state,
            "message": "Monster corrected and moved to PENDING_REVIEW"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error correcting monster {monster_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    service: AdminService = Depends(get_admin_service)
):
    """
    Récupère les statistiques du dashboard admin.
    
    Inclut :
    - Nombre total de monstres
    - Répartition par état
    - Taux de transmission
    - Temps moyen de review
    - Activité récente
    """
    try:
        return service.get_dashboard_stats()
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Garder les anciens endpoints pour compatibilité
# /admin/defective, etc.
```

**✅ Tests :**
- Tester chaque endpoint avec Swagger
- Valider les codes HTTP
- Tester les cas d'erreur (404, 400, 500)

---

## 📋 Phase 4 : Transmission vers API Invocation (2-3h)

### Objectif
Implémenter la transmission des monstres approuvés vers l'API d'invocation.

### 4.1 Créer le client API Invocation

**Fichier : `app/clients/invocation_api.py` (nouveau)**

Copier le contenu depuis `TECHNICAL_SPECIFICATIONS.md` section "InvocationApiClient".

**✅ Tests unitaires :**
```python
# tests/test_invocation_client.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_mapping():
    client = InvocationApiClient()
    our_format = {...}  # Notre format
    
    mapped = client._map_monster_to_invocation_format(our_format)
    
    assert mapped["name"] == our_format["nom"]
    assert mapped["rank"] == our_format["rang"]

@pytest.mark.asyncio
async def test_successful_transmission(mock_httpx):
    # Mock successful response
    ...

@pytest.mark.asyncio
async def test_retry_logic(mock_httpx):
    # Mock failures then success
    ...
```

### 4.2 Créer le TransmissionService

**Fichier : `app/services/transmission_service.py` (nouveau)**

```python
from typing import Optional, List
from app.clients.invocation_api import InvocationApiClient, InvocationApiError
from app.repositories.monster_repository import MonsterRepository
from app.services.state_manager import MonsterStateManager
from app.core.constants import MonsterState
from app.schemas.metadata import MonsterMetadata
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TransmissionService:
    """Service de transmission des monstres vers l'API d'invocation"""
    
    def __init__(self, invocation_api_url: str = "http://localhost:8085"):
        self.invocation_client = InvocationApiClient(base_url=invocation_api_url)
        self.repository = MonsterRepository()
        self.state_manager = MonsterStateManager()
    
    async def transmit_monster(self, monster_id: str, force: bool = False) -> dict:
        """
        Transmet un monstre vers l'API d'invocation.
        
        Args:
            monster_id: ID du monstre à transmettre
            force: Si True, retransmet même si déjà transmis
            
        Returns:
            dict avec le résultat de la transmission
            
        Raises:
            ValueError: Si le monstre n'est pas dans l'état approprié
            InvocationApiError: Si la transmission échoue
        """
        # Récupérer le monstre
        monster = self.repository.get(monster_id)
        if not monster:
            raise ValueError(f"Monster {monster_id} not found")
        
        # Vérifier l'état
        if monster.metadata.state == MonsterState.TRANSMITTED and not force:
            return {
                "status": "already_transmitted",
                "monster_id": monster_id,
                "transmitted_at": monster.metadata.transmitted_at,
                "message": "Monster already transmitted. Use force=true to retransmit."
            }
        
        if monster.metadata.state != MonsterState.APPROVED and not force:
            raise ValueError(
                f"Monster must be in APPROVED state, current: {monster.metadata.state}"
            )
        
        # Tenter la transmission
        try:
            response = await self.invocation_client.create_monster(
                monster.monster_data
            )
            
            # Mettre à jour les métadonnées
            monster.metadata.transmitted_at = datetime.utcnow()
            monster.metadata.transmission_attempts += 1
            monster.metadata.last_transmission_error = None
            monster.metadata.invocation_api_id = response.get("id")
            
            # Transition vers TRANSMITTED
            metadata = self.state_manager.transition(
                monster.metadata,
                MonsterState.TRANSMITTED,
                actor="system",
                note="Successfully transmitted to invocation API"
            )
            
            # Sauvegarder
            self.repository.save(metadata, monster.monster_data)
            self.repository.move_to_state(monster_id, MonsterState.TRANSMITTED)
            
            logger.info(f"Monster {monster_id} transmitted successfully")
            
            return {
                "status": "success",
                "monster_id": monster_id,
                "invocation_api_id": response.get("id"),
                "transmitted_at": metadata.transmitted_at,
                "message": "Monster transmitted successfully"
            }
            
        except InvocationApiError as e:
            # Enregistrer l'erreur
            monster.metadata.transmission_attempts += 1
            monster.metadata.last_transmission_error = str(e)
            monster.metadata.updated_at = datetime.utcnow()
            
            self.repository.save(monster.metadata, monster.monster_data)
            
            logger.error(f"Failed to transmit monster {monster_id}: {e}")
            
            raise
    
    async def transmit_all_approved(self, max_count: Optional[int] = None) -> dict:
        """
        Transmet tous les monstres approuvés.
        
        Args:
            max_count: Nombre maximum à transmettre (None = tous)
            
        Returns:
            dict avec les résultats de la transmission
        """
        approved_monsters = self.repository.list_by_state(
            MonsterState.APPROVED,
            limit=max_count or 1000
        )
        
        results = {
            "total": len(approved_monsters),
            "success": 0,
            "failed": 0,
            "details": []
        }
        
        for metadata in approved_monsters:
            try:
                result = await self.transmit_monster(metadata.monster_id)
                results["success"] += 1
                results["details"].append({
                    "monster_id": metadata.monster_id,
                    "status": "success"
                })
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "monster_id": metadata.monster_id,
                    "status": "failed",
                    "error": str(e)
                })
        
        logger.info(
            f"Batch transmission completed: "
            f"{results['success']} success, {results['failed']} failed"
        )
        
        return results
    
    async def health_check(self) -> dict:
        """Vérifie la disponibilité de l'API d'invocation"""
        is_healthy = await self.invocation_client.health_check()
        
        return {
            "invocation_api_healthy": is_healthy,
            "base_url": self.invocation_client.base_url
        }
```

### 4.3 Créer les endpoints de transmission

**Fichier : `app/api/v1/endpoints/transmission.py` (nouveau)**

```python
from fastapi import APIRouter, HTTPException, Depends
from app.services.transmission_service import TransmissionService
from app.schemas.admin import TransmitRequest
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

def get_transmission_service() -> TransmissionService:
    """Dependency injection"""
    return TransmissionService(invocation_api_url=settings.INVOCATION_API_URL)

@router.post("/transmit/{monster_id}")
async def transmit_monster(
    monster_id: str,
    force: bool = False,
    service: TransmissionService = Depends(get_transmission_service)
):
    """
    Transmet un monstre approuvé vers l'API d'invocation.
    
    - Le monstre doit être en état APPROVED (sauf si force=true)
    - Après transmission réussie, passe en état TRANSMITTED
    - Retry automatique en cas d'échec
    """
    try:
        result = await service.transmit_monster(monster_id, force)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error transmitting monster {monster_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Transmission failed: {str(e)}")

@router.post("/transmit-batch")
async def transmit_batch(
    max_count: int = None,
    service: TransmissionService = Depends(get_transmission_service)
):
    """
    Transmet tous les monstres approuvés en batch.
    
    - **max_count**: Nombre maximum à transmettre (optionnel)
    
    Retourne un rapport détaillé avec succès et échecs.
    """
    try:
        result = await service.transmit_all_approved(max_count)
        return result
    except Exception as e:
        logger.error(f"Error in batch transmission: {e}")
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/health-check")
async def health_check(
    service: TransmissionService = Depends(get_transmission_service)
):
    """Vérifie la disponibilité de l'API d'invocation"""
    try:
        result = await service.health_check()
        return result
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 4.4 Enregistrer le router

**Fichier : `app/main.py`**

```python
# Ajouter l'import
from app.api.v1.endpoints import gatcha, nano_banana, admin, transmission

# Ajouter le router
app.include_router(
    transmission.router,
    prefix=f"{settings.API_V1_STR}/transmission",
    tags=["transmission"],
)
```

**✅ Tests d'intégration :**
- Démarrer l'API d'invocation (mock ou réelle)
- Créer un monstre → approuver → transmettre
- Vérifier qu'il est bien dans TRANSMITTED
- Tester le batch transmission

---

## 📋 Phase 5 : Refactoring et optimisation (2-3h)

### Objectif
Nettoyer le code, optimiser, et améliorer la maintenabilité.

### 5.1 Nettoyer FileManager

**Fichier : `app/utils/file_manager.py`**

- Migrer les fonctionnalités vers `MonsterRepository`
- Garder uniquement les méthodes génériques (save_image, sanitize_filename)
- Supprimer les méthodes dupliquées

### 5.2 Ajouter la gestion de configuration

**Fichier : `app/api/v1/endpoints/admin.py`**

```python
@router.get("/config")
async def get_config():
    """Récupère la configuration actuelle"""
    settings = get_settings()
    return {
        "auto_transmit_enabled": settings.AUTO_TRANSMIT_ENABLED,
        "invocation_api_url": settings.INVOCATION_API_URL,
        "max_retry_attempts": settings.INVOCATION_API_MAX_RETRIES,
        "retry_delay_seconds": settings.INVOCATION_API_RETRY_DELAY,
    }

@router.put("/config")
async def update_config(config: ConfigUpdate):
    """
    Mettre à jour la configuration.
    
    Note: Pour l'instant, ceci nécessite un redémarrage.
    TODO: Implémenter le hot-reload de la config.
    """
    # TODO: Implémenter la mise à jour dynamique
    raise HTTPException(
        status_code=501,
        detail="Configuration update not implemented yet. Modify .env and restart."
    )
```

### 5.3 Améliorer le logging

**Fichier : `app/core/logging_config.py` (nouveau)**

```python
import logging
from logging.handlers import RotatingFileHandler
import sys

def setup_logging():
    """Configure le logging pour l'application"""
    
    # Format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # File handler (rotating)
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Silencer les logs trop verbeux
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
```

**Fichier : `app/main.py`**

```python
from app.core.logging_config import setup_logging
import os

# Setup logging
os.makedirs("logs", exist_ok=True)
setup_logging()

# ... reste du code
```

### 5.4 Ajouter des constantes

**Fichier : `app/core/constants.py` (nouveau)**

```python
"""Constantes globales de l'application"""

# Messages d'erreur
ERROR_MONSTER_NOT_FOUND = "Monster not found"
ERROR_INVALID_TRANSITION = "Invalid state transition"
ERROR_TRANSMISSION_FAILED = "Failed to transmit monster to invocation API"
ERROR_VALIDATION_FAILED = "Monster validation failed"

# Messages de succès
SUCCESS_MONSTER_GENERATED = "Monster generated successfully"
SUCCESS_MONSTER_APPROVED = "Monster approved successfully"
SUCCESS_MONSTER_TRANSMITTED = "Monster transmitted successfully"

# Limites
MAX_BATCH_SIZE = 15
MAX_LIST_LIMIT = 200
DEFAULT_LIST_LIMIT = 50

# Timeouts (secondes)
DEFAULT_API_TIMEOUT = 30
HEALTH_CHECK_TIMEOUT = 5
```

---

## 📋 Phase 6 : Tests et documentation (2-3h)

### Objective
Assurer la qualité du code et documenter l'API.

### 6.1 Tests unitaires

**Fichier : `tests/test_state_manager.py`** (déjà fait en Phase 2)

**Fichier : `tests/test_repository.py`** (déjà fait en Phase 2)

**Fichier : `tests/test_invocation_client.py`** (voir Phase 4)

**Fichier : `tests/test_admin_service.py` (nouveau)**

```python
import pytest
from app.services.admin_service import AdminService
from app.core.constants import MonsterState, TransitionAction

def test_list_monsters():
    service = AdminService()
    results = service.list_monsters(limit=10)
    assert isinstance(results, list)

def test_get_monster_detail(test_monster_id):
    service = AdminService()
    detail = service.get_monster_detail(test_monster_id)
    assert detail is not None

def test_review_approve():
    # ... test d'approbation
    pass

def test_review_reject():
    # ... test de rejet
    pass

def test_correct_defective():
    # ... test de correction
    pass
```

### 6.2 Tests d'intégration

**Fichier : `tests/integration/test_full_workflow.py` (nouveau)**

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_full_workflow_success():
    """Test du workflow complet : génération → review → transmission"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Générer un monstre
        response = await client.post(
            "/api/v1/monsters/generate",
            json={"prompt": "Test monster"}
        )
        assert response.status_code == 200
        monster = response.json()
        
        # 2. Récupérer l'ID depuis les métadonnées
        # ... (à adapter selon l'implémentation)
        
        # 3. Approuver le monstre
        response = await client.post(
            f"/api/v1/admin/monsters/{monster_id}/review",
            json={"action": "approve", "notes": "Test approval"}
        )
        assert response.status_code == 200
        
        # 4. Transmettre le monstre
        response = await client.post(
            f"/api/v1/transmission/transmit/{monster_id}"
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
```

### 6.3 Documentation complète

**Fichier : `API_DOCUMENTATION.md` (nouveau)**

Créer une documentation complète des endpoints avec :
- Description de chaque endpoint
- Paramètres requis et optionnels
- Exemples de requêtes curl
- Exemples de réponses
- Codes d'erreur possibles

**Fichier : `DEPLOYMENT.md` (nouveau)**

```markdown
# Guide de Déploiement

## Prérequis
- Python 3.9+
- Docker & Docker Compose
- API Invocation accessible

## Installation

1. Clone du repo
2. Créer un .env
3. Installer les dépendances
4. Migrer les données existantes
5. Lancer l'application

## Configuration

### Variables d'environnement

...

## Migration

...

## Monitoring

...
```

### 6.4 README mis à jour

**Fichier : `README.md`**

Mettre à jour avec :
- Nouvelles fonctionnalités
- Architecture mise à jour
- Guide de démarrage rapide
- Liens vers les autres docs

---

## ✅ Checklist finale

### Avant de commencer
- [ ] Backup de tous les fichiers existants
- [ ] Backup de la base de données / JSONs existants
- [ ] Lire toute la documentation
- [ ] Préparer l'environnement de dev

### Phase 1
- [ ] Enums créés
- [ ] Schémas créés
- [ ] Configuration mise à jour
- [ ] Dossiers créés
- [ ] Migration des JSONs existants

### Phase 2
- [ ] StateManager implémenté et testé
- [ ] Repository implémenté et testé
- [ ] GatchaService refactoré

### Phase 3
- [ ] AdminService implémenté
- [ ] Endpoints admin créés
- [ ] Tests Swagger OK

### Phase 4
- [ ] Client API Invocation créé
- [ ] TransmissionService créé
- [ ] Endpoints transmission créés
- [ ] Tests d'intégration OK

### Phase 5
- [ ] Code nettoyé
- [ ] Logging configuré
- [ ] Configuration dynamique

### Phase 6
- [ ] Tests unitaires écrits et passent
- [ ] Tests d'intégration écrits et passent
- [ ] Documentation complète
- [ ] README mis à jour

### Déploiement
- [ ] Tests sur environnement de staging
- [ ] Validation par l'équipe
- [ ] Migration en production
- [ ] Monitoring mis en place

---

## 🚀 Commandes utiles

### Développement

```bash
# Lancer l'API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Lancer les tests
pytest tests/ -v

# Lancer les tests avec coverage
pytest tests/ --cov=app --cov-report=html

# Migration
python scripts/setup_directories.py
python scripts/migrate_existing_monsters.py

# Check du code
black app/
flake8 app/
mypy app/
```

### Docker

```bash
# Build
docker-compose build

# Lancer
docker-compose up -d

# Logs
docker-compose logs -f api

# Stop
docker-compose down
```

---

## 📞 Support

En cas de problème pendant l'implémentation :
1. Vérifier les logs
2. Vérifier la configuration
3. Consulter la documentation technique
4. Exécuter les tests pour identifier le problème

---

**Note finale** : Cette roadmap est conçue pour être suivie séquentiellement. Chaque phase construit sur la précédente. Ne sautez pas d'étapes et testez systématiquement après chaque phase !
