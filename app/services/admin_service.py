"""
Module: admin_service

Description:
Service d'administration des monstres - Orchestration des workflows admin
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session

from app.repositories.monster.repository import MonsterRepository
from app.repositories.monster.state_repository import MonsterStateRepository
from app.repositories.monster.transition_repository import TransitionRepository
from app.schemas.json_monster import MonsterBase
from app.services.state_manager import MonsterStateManager
from app.services.validation_service import MonsterValidationService
from app.schemas.metadata import MonsterMetadata
from app.core.constants import (
    ElementEnum,
    MonsterStateEnum,
    RankEnum,
    TransitionActionEnum,
)
from app.schemas.admin import (
    MonsterListFilter,
    MonsterSummary,
    MonsterDetail,
    DashboardStats,
)
from app.services.monster_mapper import (
    map_json_monster,
    map_monster_to_json,
    map_monster_to_summary,
    map_monster_metadata_to_summary,
)


logger = logging.getLogger(__name__)


class AdminService:
    """Service d'administration des monstres"""

    def __init__(self, db: Session):
        self.state_repository = MonsterStateRepository(db)
        self.structure_repository = TransitionRepository(db)
        self.monster_repository = MonsterRepository(db)
        self.state_manager = MonsterStateManager()
        self.validation_service = MonsterValidationService()

    def list_monsters(
        self,
        filter: Optional[MonsterListFilter] = None,
    ) -> List[MonsterSummary]:
        """Liste les monstres avec filtres"""

        if filter:
            # Il filtre par state, is valid, il ordonne et il prend le bon limit/offset
            metadata_list = self.state_repository.list_filtred(filter)
        else:
            metadata_list = self.state_repository.list_all()

        summaries = []
        for metadata in metadata_list:
            if metadata.monster:
                monster = self.monster_repository.get_by_uuid(metadata.monster_id)
                if monster:
                    summaries.append(map_monster_to_summary(metadata, monster))
            else:
                monster = self.state_repository.get(metadata.monster_id)
                if monster:
                    summaries.append(map_monster_metadata_to_summary(metadata, monster))

        return self.filter_monsters(
            summaries,
            element=filter.element if filter else None,
            rank=filter.rank if filter else None,
            search=filter.search if filter else None,
        )

    def filter_monsters(
        self,
        summaries: List[MonsterSummary],
        element: Optional[ElementEnum] = None,
        rank: Optional[RankEnum] = None,
        search: Optional[str] = None,
    ) -> List[MonsterSummary]:
        """Filtre les monstres par élément, rang et recherche textuelle"""
        filtered_summaries = []
        for summary in summaries:
            if element is not None and summary.element != element:
                continue
            if rank is not None and summary.rank != rank:
                continue
            if search is not None and search.lower() not in summary.name.lower():
                continue
            filtered_summaries.append(summary)
        return filtered_summaries

    def get_monster_detail(self, monster_id: str) -> Optional[MonsterDetail]:
        """Récupère les détails complets d'un monstre"""

        monster = self.state_repository.get(monster_id)
        if not monster:
            return None

        # Validation report si erreurs
        validation_report = None
        if not monster.metadata.is_valid and monster.metadata.validation_errors:
            validation_report = {
                "is_valid": False,
                "errors": monster.metadata.validation_errors,
            }

        if monster.metadata.monster:
            structured_monster = self.monster_repository.get_by_uuid(monster_id)
            if not structured_monster:
                logger.warning(f"Structured monster not found for UUID: {monster_id}")
                return None
            # Monstre structuré
            return MonsterDetail(
                metadata=monster.metadata,
                monster_data=map_monster_to_json(structured_monster),
                image_url=monster.monster_data.get("ImageUrl", ""),
            )
        else:
            # Construire l'URL de l'image
            image_url = monster.monster_data.get("ImageUrl", "")

            return MonsterDetail(
                metadata=monster.metadata,
                monster_data=monster.monster_data,
                image_url=image_url,
                validation_report=validation_report,
            )

    def review_monster(
        self,
        monster_id: str,
        action: TransitionActionEnum,
        notes: Optional[str] = None,
        corrected_data: Optional[MonsterBase] = None,
        admin_name: str = "admin",
    ) -> MonsterMetadata:
        """Review un monstre (approve ou reject)"""

        monster = self.state_repository.get(monster_id)
        if not monster:
            raise ValueError(f"Monster {monster_id} not found")

        # Vérifier l'état actuel
        if monster.metadata.state != MonsterStateEnum.PENDING_REVIEW:
            raise ValueError(
                f"Monster must be in PENDING_REVIEW state, current: {monster.metadata.state}"
            )

        # Déterminer l'état cible
        if action == TransitionActionEnum.APPROVE:
            target_state = MonsterStateEnum.APPROVED
        elif action == TransitionActionEnum.REJECT:
            target_state = MonsterStateEnum.REJECTED
        else:
            raise ValueError(f"Invalid action: {action}")

        # Si corrected_data fourni, valider et mettre à jour
        if corrected_data:
            validation_result = self.validation_service.validate(
                map_json_monster(corrected_data)
            )
            if not validation_result.is_valid:
                raise ValueError(
                    "Corrected data is invalid", validation_result.to_dict()
                )

        # Mettre à jour les métadonnées
        monster.metadata.reviewed_by = admin_name
        monster.metadata.review_date = datetime.now(timezone.utc)
        monster.metadata.review_notes = notes

        # Transition d'état
        metadata = self.state_manager.transition(
            monster.metadata,
            target_state,
            actor=admin_name,
            note=notes or f"Review: {action.value}",
        )

        # Sauvegarder
        self.state_repository.save(metadata)
        self.structure_repository.move_to_state(
            monster_id,
            target_state,
            actor=admin_name,
            note=notes or f"Review: {action.value}",
        )

        logger.info(f"Monster {monster_id} reviewed: {action.value} by {admin_name}")

        return metadata

    def correct_defective(
        self,
        monster_id: str,
        corrected_data: Dict[str, Any],
        notes: Optional[str] = None,
        admin_name: str = "admin",
    ) -> MonsterMetadata:
        """Corrige un monstre défectueux"""

        monster = self.state_repository.get(monster_id)
        if not monster:
            raise ValueError(f"Monster {monster_id} not found")

        if monster.metadata.state != MonsterStateEnum.DEFECTIVE:
            raise ValueError(
                f"Monster must be in DEFECTIVE state, current: {monster.metadata.state}"
            )

        # Valider les données corrigées
        validation_result = self.validation_service.validate(corrected_data)
        if not validation_result.is_valid:
            raise ValueError(
                "Corrected data is still invalid", validation_result.to_dict()
            )

        # Mettre à jour les données
        monster.monster_data = corrected_data
        monster.metadata.is_valid = True
        monster.metadata.validation_errors = None

        # Transition DEFECTIVE → CORRECTED → PENDING_REVIEW
        metadata = self.state_manager.transition(
            monster.metadata,
            MonsterStateEnum.CORRECTED,
            actor=admin_name,
            note=notes or "Corrected by admin",
        )

        self.state_repository.save(metadata, monster.monster_data)
        self.structure_repository.move_to_state(
            monster_id,
            MonsterStateEnum.CORRECTED,
            actor=admin_name,
            note=notes or "Corrected by admin",
        )

        # Auto-transition vers PENDING_REVIEW
        metadata = self.state_manager.transition(
            metadata,
            MonsterStateEnum.PENDING_REVIEW,
            actor="system",
            note="Auto-transition after correction",
        )

        self.state_repository.save(metadata, monster.monster_data)
        self.structure_repository.move_to_state(
            monster_id,
            MonsterStateEnum.PENDING_REVIEW,
            actor="system",
            note="Auto-transition after correction",
        )

        logger.info(f"Monster {monster_id} corrected by {admin_name}")

        return metadata

    def get_dashboard_stats(self) -> DashboardStats:
        """Récupère les statistiques du dashboard"""

        # Compter par état
        counts = self.state_repository.count_by_state()

        total = sum(counts.values())
        transmitted = counts.get(MonsterStateEnum.TRANSMITTED.value, 0)
        transmission_rate = transmitted / total if total > 0 else 0.0

        # Activité récente (dernières transitions)
        recent_activity = []
        all_metadata = self.state_repository.list_all(limit=20)

        for metadata in all_metadata:
            if metadata.history:
                monster = self.state_repository.get(metadata.monster_id)
                monster_name = (
                    monster.monster_data.get("nom", "Unknown") if monster else "Unknown"
                )
                last_transition = metadata.history[-1]
                recent_activity.append(
                    {
                        "monster_id": metadata.monster_id,
                        "monster_name": monster_name,
                        "transition": f"{last_transition.from_state} → {last_transition.to_state}",
                        "timestamp": last_transition.timestamp,
                        "actor": last_transition.actor,
                    }
                )

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
            recent_activity=recent_activity[:10],
        )

    def process_generated_monsters(self) -> Dict[str, Any]:
        """
        Traite tous les monstres en état GENERATED.

        Pour chaque monstre:
        - Valide les données
        - Si valide: transition vers PENDING_REVIEW
        - Si invalide: transition vers DEFECTIVE

        Returns:
            Dictionnaire avec le résumé du traitement
        """
        # Récupérer tous les monstres en état GENERATED
        generated_monsters = self.state_repository.list_filtred(
            MonsterListFilter(
                state=MonsterStateEnum.GENERATED,
                limit=100,  # Large limite pour tout traiter
                offset=0,
            )
        )

        total_processed = len(generated_monsters)
        moved_to_pending_review = 0
        moved_to_defective = 0
        details = []

        logger.info(f"Processing {total_processed} monsters in GENERATED state")

        for metadata in generated_monsters:
            monster_id = metadata.monster_id

            try:
                # Récupérer les données complètes du monstre
                monster = self.state_repository.get(monster_id)
                if not monster:
                    logger.warning(f"Monster {monster_id} not found, skipping")
                    continue

                # Valider les données
                validation_result = self.validation_service.validate(
                    monster.monster_data
                )

                if validation_result.is_valid:
                    # Déplacer vers PENDING_REVIEW
                    self.structure_repository.move_to_state(
                        monster_id,
                        MonsterStateEnum.PENDING_REVIEW,
                        actor="system",
                        note="Auto-transition after bulk validation",
                    )
                    # Mettre à jour les métadonnées locales
                    monster.metadata.state = MonsterStateEnum.PENDING_REVIEW
                    monster.metadata.updated_at = datetime.now(timezone.utc)

                    moved_to_pending_review += 1

                    details.append(
                        {
                            "monster_id": monster_id,
                            "name": monster.monster_data.get("nom", "Unknown"),
                            "action": "moved_to_pending_review",
                            "is_valid": True,
                        }
                    )

                    logger.info(
                        f"Monster {monster_id} validated and moved to PENDING_REVIEW"
                    )

                else:
                    # Préparer les erreurs de validation
                    validation_errors = [
                        {
                            "field": e.field,
                            "error_type": e.error_type,
                            "message": e.message,
                        }
                        for e in validation_result.errors
                    ]

                    # Mettre à jour les métadonnées avec les erreurs
                    monster.metadata.is_valid = False
                    monster.metadata.validation_errors = validation_errors
                    monster.metadata.state = MonsterStateEnum.DEFECTIVE
                    monster.metadata.updated_at = datetime.now(timezone.utc)

                    # Sauvegarder les métadonnées mises à jour
                    self.state_repository.save(monster.metadata, monster.monster_data)

                    # Déplacer vers DEFECTIVE
                    self.structure_repository.move_to_state(
                        monster_id, MonsterStateEnum.DEFECTIVE
                    )
                    moved_to_defective += 1

                    details.append(
                        {
                            "monster_id": monster_id,
                            "name": monster.monster_data.get("nom", "Unknown"),
                            "action": "moved_to_defective",
                            "is_valid": False,
                            "error_count": len(validation_errors),
                        }
                    )

                    logger.warning(
                        f"Monster {monster_id} invalid and moved to DEFECTIVE"
                    )

            except Exception as e:
                logger.error(f"Error processing monster {monster_id}: {e}")
                details.append(
                    {"monster_id": monster_id, "action": "error", "error": str(e)}
                )

        logger.info(
            f"Processing complete: {moved_to_pending_review} to PENDING_REVIEW, "
            f"{moved_to_defective} to DEFECTIVE"
        )

        return {
            "total_processed": total_processed,
            "moved_to_pending_review": moved_to_pending_review,
            "moved_to_defective": moved_to_defective,
            "details": details,
        }
