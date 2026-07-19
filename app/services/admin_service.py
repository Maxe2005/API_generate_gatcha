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
from app.repositories.monster.update_event_repository import UpdateEventRepository
from app.services.state_manager import MonsterStateManager
from app.services.validation_service import MonsterValidationService
from app.services.monster_modification_service import MonsterModificationService
from app.schemas.metadata import MonsterMetadata
from app.core.constants import (
    ElementEnum,
    MonsterStateEnum,
    RankEnum,
)
from app.schemas.admin import (
    MonsterListFilter,
    MonsterSummary,
    MonsterDetail,
    DashboardStats,
    MonsterStatsByStateResponse,
)
from app.services.mappeur.monster_mapper import (
    map_monster_to_json,
    map_monster_to_summary,
    map_monster_metadata_to_summary,
    map_payload_to_monster_update,
    map_structured_to_json,
)

from app.utils.changed_fields import compute_changed_fields


logger = logging.getLogger(__name__)


class AdminService:
    """Service d'administration des monstres"""

    _STATS_STATE_HIERARCHY = [
        MonsterStateEnum.PENDING_REVIEW,
        MonsterStateEnum.APPROVED,
        MonsterStateEnum.TRANSMITTED,
    ]

    def __init__(self, db: Session):
        self.state_repository = MonsterStateRepository(db)
        self.structure_repository = TransitionRepository(db)
        self.monster_repository = MonsterRepository(db)
        self.update_event_repository = UpdateEventRepository(db)
        self.state_manager = MonsterStateManager(
            self.state_repository, self.structure_repository
        )
        self.validation_service = MonsterValidationService()
        self.modification_service = MonsterModificationService(db)
        self.db = db

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
                image_url=structured_monster.image_url,  # type: ignore
            )
        else:
            if not monster.monster_data:
                logger.warning(f"Monster data is missing for monster_id: {monster_id}")
                return None
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
        notes: Optional[str] = None,
        admin_name: str = "admin",
    ) -> MonsterMetadata:
        """Review un monstre : approve"""

        monster = self.state_repository.get(monster_id)
        if not monster:
            raise ValueError(f"Monster {monster_id} not found")

        # Vérifier l'état actuel
        if monster.metadata.state != MonsterStateEnum.PENDING_REVIEW:
            raise ValueError(
                f"Monster must be in PENDING_REVIEW state, current: {monster.metadata.state}"
            )

        # Vérifier que les données actuelles sont valides
        if monster.monster_data:
            raise ValueError(
                "Monster data is still in json format (usually impossible in PENDING_REVIEW state)"
            )

        # Mettre à jour les métadonnées
        monster.metadata.reviewed_by = admin_name
        monster.metadata.review_date = datetime.now(timezone.utc)
        monster.metadata.review_notes = notes

        # Transition d'état
        metadata = self.state_manager.perform_transition(
            monster.metadata,
            MonsterStateEnum.APPROVED,
            monster_data=monster.monster_data,
            actor=admin_name,
            note=notes or f"Review: APPROVED by {admin_name}",
        )

        logger.info(f"Monster {monster_id} reviewed: APPROVED by {admin_name}")

        return metadata

    def correct_defective(
        self,
        monster_id: str,
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

        # Vérifier que les données actuelles sont valides
        if not monster.monster_data:
            raise ValueError("Monster data is missing")

        validation_result = self.validation_service.validate(monster.monster_data)
        if not validation_result.is_valid:
            raise ValueError(
                "Cannot correct monster: current data is still invalid. Please update the monster data first.",
                validation_result.to_dict(),
            )

        # Mettre à jour les métadonnées de validation
        monster.metadata.is_valid = True
        monster.metadata.validation_errors = None

        # Auto-transition vers PENDING_REVIEW
        metadata = self.state_manager.perform_transition(
            monster.metadata,
            MonsterStateEnum.PENDING_REVIEW,
            monster_data=monster.monster_data,
            actor=admin_name,
            note=notes or f"Corrected by admin {admin_name}",
        )

        logger.info(f"Monster {monster_id} corrected by {admin_name}")

        return metadata

    def update_monster_data(
        self,
        monster_id: str,
        monster_data: Dict[str, Any],
        skip_validation: bool = False,
        notes: Optional[str] = None,
        admin_name: str = "admin",
    ) -> MonsterMetadata:
        """Met à jour les données d'un monstre"""

        monster = self.state_repository.get(monster_id)
        if not monster:
            raise ValueError(f"Monster {monster_id} not found")

        # Vérifier que le monstre est dans un état modifiable
        modifiable_states = [
            MonsterStateEnum.GENERATED,
            MonsterStateEnum.PENDING_REVIEW,
            MonsterStateEnum.DEFECTIVE,
        ]
        if monster.metadata.state not in modifiable_states:
            raise ValueError(
                f"Monster cannot be updated in state {monster.metadata.state}. "
                f"Allowed states: {[s.value for s in modifiable_states]}"
            )

        # Mémoriser l'état avant
        validation_before = monster.metadata.is_valid
        old_data = None
        structured_monster = bool(monster.metadata.monster)
        if structured_monster:
            structured_monster = self.monster_repository.get_by_uuid(monster_id)
            old_data = map_structured_to_json(structured_monster)
        else :
            old_data = monster.monster_data.copy() if monster.monster_data else {}

        # Valider les nouvelles données si nécessaire
        validation_result = self.validation_service.validate(monster_data)
        if not validation_result.is_valid and not skip_validation:
            raise ValueError(
                "Monster data is invalid. Set skip_validation=True to force update.",
                validation_result.to_dict(),
            )

        # Mettre à jour les erreurs de validation
        if validation_result.is_valid:
            monster.metadata.validation_errors = None
        else:
            monster.metadata.validation_errors = [
                {
                    "field": e.field,
                    "error_type": e.error_type,
                    "message": e.message,
                }
                for e in validation_result.errors
            ]

        
        if (
            structured_monster
            != monster.metadata.state
            in [
                MonsterStateEnum.PENDING_REVIEW,
                MonsterStateEnum.APPROVED,
            ]
        ):
            logger.warning(
                f"Monster {monster_id} has inconsistent structured_monster={structured_monster} "
                f"and state={monster.metadata.state}"
            )
        # Calculer les changed_fields et diff pour JSON
        change_info = compute_changed_fields(old_data, monster_data)
        changed_fields = change_info["changed_fields"]
        diff_payload = change_info["diff_payload"]
        # Déterminer si c'est un monstre JSON ou structuré
        if structured_monster:
            # Monstre structuré : modifier via MonsterModificationService
            try:
                # Convertir les données reçues en MonsterUpdate
                updates = map_payload_to_monster_update(monster_data)

                # Utiliser le service de modification pour les monstres structurés
                self.modification_service.update_monster(
                    monster_id=monster_id,
                    updates=updates,
                    actor=admin_name,
                )

            except ValueError as e:
                raise ValueError(f"Invalid data for structured monster: {str(e)}")
            except Exception as e:
                logger.error(f"Error updating structured monster {monster_id}: {e}")
                raise ValueError(f"Failed to update monster data: {str(e)}")
        else:
            monster.monster_data = monster_data

        monster.metadata.is_valid = validation_result.is_valid
        monster.metadata.updated_at = datetime.now(timezone.utc)

        self.state_repository.save(
            monster.metadata, monster.monster_data if not structured_monster else None
        )

        self.update_event_repository.create(
            monster_id=monster_id,
            actor_type="admin",
            actor_name=admin_name,
            validation_before=validation_before,
            validation_after=validation_result.is_valid,
            changed_fields=changed_fields,
            reason=notes
            or f"Data updated (valid={validation_result.is_valid}, skip_validation={skip_validation})",
            skip_validation=skip_validation,
            diff_payload=diff_payload,
        )

        # Re-récupérer le monstre depuis la BD pour avoir les données fraîches
        updated_monster = self.state_repository.get(monster_id)
        if not updated_monster:
            logger.error(f"Failed to re-fetch monster {monster_id} after update")
            raise ValueError(f"Failed to re-fetch monster {monster_id} after update")

        logger.info(
            f"Monster {monster_id} data updated by {admin_name} "
            f"(valid={validation_result.is_valid}, skip_validation={skip_validation})"
        )

        return updated_monster.metadata

    def reject_monster(
        self,
        monster_id: str,
        notes: Optional[str] = None,
        admin_name: str = "admin",
    ) -> MonsterMetadata:
        """Rejette un monstre"""

        monster = self.state_repository.get(monster_id)
        if not monster:
            raise ValueError(f"Monster {monster_id} not found")

        # Vérifier que le monstre est dans un état rejectable
        rejectable_states = [
            MonsterStateEnum.GENERATED,
            MonsterStateEnum.PENDING_REVIEW,
            MonsterStateEnum.DEFECTIVE,
        ]
        if monster.metadata.state not in rejectable_states:
            raise ValueError(
                f"Monster cannot be rejected in state {monster.metadata.state}. "
                f"Allowed states: {[s.value for s in rejectable_states]}"
            )

        # Mettre à jour les métadonnées
        monster.metadata.reviewed_by = admin_name
        monster.metadata.review_date = datetime.now(timezone.utc)
        monster.metadata.review_notes = notes

        # Transition vers REJECTED
        metadata = self.state_manager.perform_transition(
            monster.metadata,
            MonsterStateEnum.REJECTED,
            monster_data=monster.monster_data,
            actor=admin_name,
            note=notes or f"Rejected by admin {admin_name}",
        )

        logger.info(f"Monster {monster_id} rejected by {admin_name}")

        return metadata

    def get_monster_name(self, monster_id: str) -> Optional[str]:
        """Récupère le nom d'un monstre à partir de son ID"""

        monster = self.state_repository.get(monster_id)
        if not monster:
            return None

        if monster.metadata.monster:
            structured_monster = self.monster_repository.get_by_uuid(monster_id)
            if not structured_monster:
                logger.warning(f"Structured monster not found for UUID: {monster_id}")
                return None
            return structured_monster.name  # type: ignore
        else:
            if not monster.monster_data:
                logger.warning(f"Monster data is missing for monster_id: {monster_id}")
                return None
            return monster.monster_data.get("name", "Unknown")

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
                monster_name = self.get_monster_name(metadata.monster_id)
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

    def get_stats_by_state(
        self, state: MonsterStateEnum
    ) -> MonsterStatsByStateResponse:
        """
        Récupère les statistiques min/moyenne/max des stats par état minimum.

        Hiérarchie appliquée:
        - PENDING_REVIEW -> [PENDING_REVIEW, APPROVED, TRANSMITTED]
        - APPROVED -> [APPROVED, TRANSMITTED]
        - TRANSMITTED -> [TRANSMITTED]
        """
        if state not in self._STATS_STATE_HIERARCHY:
            allowed = [s.value for s in self._STATS_STATE_HIERARCHY]
            raise ValueError(
                f"Invalid state for stats hierarchy: {state.value}. Allowed: {allowed}"
            )

        min_index = self._STATS_STATE_HIERARCHY.index(state)
        selected_states = self._STATS_STATE_HIERARCHY[min_index:]
        stats = self.monster_repository.get_stats_by_states(selected_states)

        return MonsterStatsByStateResponse(
            state=state,
            total_monsters=stats["total_monsters"],
            hp=stats["hp"],
            vit=stats["vit"],
            def_=stats["def"],
            atk=stats["atk"],
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
                if not monster.monster_data:
                    logger.warning(
                        f"Monster data is missing for monster_id: {monster_id}"
                    )
                    continue
                validation_result = self.validation_service.validate(
                    monster.monster_data
                )

                if validation_result.is_valid:
                    # Déplacer vers PENDING_REVIEW

                    # Transition centralisée
                    monster.metadata = self.state_manager.perform_transition(
                        monster.metadata,
                        MonsterStateEnum.PENDING_REVIEW,
                        monster_data=monster.monster_data,
                        actor="system",
                        note="Auto-transition after bulk validation",
                    )

                    moved_to_pending_review += 1

                    details.append(
                        {
                            "monster_id": monster_id,
                            "name": monster.monster_data.get("name", "Unknown"),
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
                    # (l'état reste GENERATED : c'est perform_transition qui
                    # applique GENERATED → DEFECTIVE, sinon la transition est rejetée)
                    monster.metadata.is_valid = False
                    monster.metadata.validation_errors = validation_errors
                    monster.metadata.updated_at = datetime.now(timezone.utc)

                    # Sauvegarder les métadonnées mises à jour
                    self.state_repository.save(monster.metadata, monster.monster_data)

                    # Déplacer vers DEFECTIVE

                    monster.metadata = self.state_manager.perform_transition(
                        monster.metadata,
                        MonsterStateEnum.DEFECTIVE,
                        monster_data=monster.monster_data,
                        actor="system",
                        note="Auto-transition after bulk validation (defective)",
                    )
                    moved_to_defective += 1

                    details.append(
                        {
                            "monster_id": monster_id,
                            "name": monster.monster_data.get("name", "Unknown"),
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

    def process_generated_monster(self, monster_id: str) -> Dict[str, Any]:
        """
        Traite un seul monstre en état GENERATED.
        Valide les données et effectue la transition appropriée.
        Retourne un résumé du traitement.
        """
        try:
            monster = self.state_repository.get(monster_id)
            if not monster:
                return {
                    "status": "error",
                    "monster_id": monster_id,
                    "error": "Monster not found",
                }
            if monster.metadata.state != MonsterStateEnum.GENERATED:
                return {
                    "status": "skipped",
                    "monster_id": monster_id,
                    "reason": f"State is {monster.metadata.state}, not GENERATED",
                }

            if not monster.monster_data:
                logger.warning(f"Monster data is missing for monster_id: {monster_id}")
                return {
                    "status": "error",
                    "monster_id": monster_id,
                    "error": "Monster data is missing",
                }
            validation_result = self.validation_service.validate(monster.monster_data)
            if validation_result.is_valid:
                monster.metadata = self.state_manager.perform_transition(
                    monster.metadata,
                    MonsterStateEnum.PENDING_REVIEW,
                    monster_data=monster.monster_data,
                    actor="system",
                    note="Auto-transition after single validation",
                )
                action = "moved_to_pending_review"
                is_valid = True
                error_count = 0
            else:
                validation_errors = [
                    {"field": e.field, "error_type": e.error_type, "message": e.message}
                    for e in validation_result.errors
                ]
                monster.metadata.is_valid = False
                monster.metadata.validation_errors = validation_errors
                monster.metadata.updated_at = datetime.now(timezone.utc)
                self.state_repository.save(monster.metadata, monster.monster_data)
                monster.metadata = self.state_manager.perform_transition(
                    monster.metadata,
                    MonsterStateEnum.DEFECTIVE,
                    monster_data=monster.monster_data,
                    actor="system",
                    note="Auto-transition after single validation (defective)",
                )
                action = "moved_to_defective"
                is_valid = False
                error_count = len(validation_errors)

            return {
                "status": "success",
                "monster_id": monster_id,
                "name": monster.monster_data.get("name", "Unknown"),
                "action": action,
                "is_valid": is_valid,
                "error_count": error_count if not is_valid else 0,
            }
        except Exception as e:
            logger.error(f"Error processing monster {monster_id}: {e}")
            return {"status": "error", "monster_id": monster_id, "error": str(e)}
