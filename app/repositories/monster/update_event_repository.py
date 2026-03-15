"""
Module: repositories.monster.update_event_repository

Description:
Repository pour la gestion des événements de mise à jour des monstres.
Persiste les updates de données de monstres à titre informatif/auditif.
"""

from typing import Optional, List
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.monster import MonsterState, UpdateEventModel
from app.schemas.update_event import UpdateEvent

logger = logging.getLogger(__name__)


class UpdateEventRepository:
    """
    Gère la persistance des événements de mise à jour des monstres.
    """

    def __init__(self, db: Session):
        """
        Initialise le repository.

        Args:
            db: Session SQLAlchemy
        """
        self.db = db

    def create(
        self,
        monster_id: str,
        actor_type: str,
        actor_name: str,
        source: str,
        validation_before: bool,
        validation_after: bool,
        storage_mode_before: str,
        storage_mode_after: str,
        changed_fields: List[str],
        actor_id: Optional[str] = None,
        reason: Optional[str] = None,
        skip_validation: bool = False,
        diff_payload: Optional[dict] = None,
        request_context: Optional[dict] = None,
    ) -> Optional[UpdateEvent]:
        """
        Crée et persiste un événement de mise à jour.

        Args:
            monster_id: UUID du monstre (pas l'ID DB, mais le monster_id)
            actor_type: admin|system|user
            actor_name: Nom de l'acteur
            source: Origine de l'update
            validation_before: État de validité avant
            validation_after: État de validité après
            storage_mode_before: json|structured avant
            storage_mode_after: json|structured après
            changed_fields: Champs modifiés
            actor_id: ID optionnel de l'acteur
            reason: Notes optionnelles
            skip_validation: Si validation a été bypass
            diff_payload: Détail des changements (before/after pour champs modifiés)
            request_context: Contexte optionnel (trace_id, etc.)

        Returns:
            UpdateEvent créé ou None en cas d'erreur
        """
        try:
            # Récupérer l'ID DB du MonsterState
            monster_state = (
                self.db.query(MonsterState)
                .filter(MonsterState.monster_id == monster_id)
                .first()
            )

            if not monster_state:
                logger.error(f"Monster state not found for {monster_id}")
                return None

            # Créer l'événement
            event = UpdateEventModel(
                monster_state_db_id=monster_state.id,
                occurred_at=datetime.now(timezone.utc),
                actor_type=actor_type,
                actor_name=actor_name,
                actor_id=actor_id,
                source=source,
                reason=reason,
                validation_before=validation_before,
                validation_after=validation_after,
                skip_validation=skip_validation,
                storage_mode_before=storage_mode_before,
                storage_mode_after=storage_mode_after,
                changed_fields=changed_fields,
                diff_payload=diff_payload or {},
                request_context=request_context or {},
            )

            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)

            logger.info(
                f"Created update event for {monster_id}: {len(changed_fields)} fields changed by {actor_name}"
            )

            # Convertir en Pydantic via dict
            return self._db_to_pydantic(event)

        except Exception as e:
            logger.error(f"Failed to create update event for {monster_id}: {e}")
            self.db.rollback()
            return None

    def get_by_monster_id(self, monster_id: str) -> List[UpdateEvent]:
        """
        Récupère tous les événements d'update d'un monstre.

        Args:
            monster_id: UUID du monstre

        Returns:
            Liste des événements triés par date (croissante)
        """
        try:
            monster_state = (
                self.db.query(MonsterState)
                .filter(MonsterState.monster_id == monster_id)
                .first()
            )

            if not monster_state:
                return []

            events = (
                self.db.query(UpdateEventModel)
                .filter(UpdateEventModel.monster_state_db_id == monster_state.id)
                .order_by(UpdateEventModel.occurred_at.asc())
                .all()
            )

            return [self._db_to_pydantic(e) for e in events]

        except Exception as e:
            logger.error(f"Failed to get update events for {monster_id}: {e}")
            return []

    def delete_by_monster_id(self, monster_id: str) -> bool:
        """Supprime tous les événements d'update d'un monstre"""
        try:
            monster_state = (
                self.db.query(MonsterState)
                .filter(MonsterState.monster_id == monster_id)
                .first()
            )

            if not monster_state:
                return False

            self.db.query(UpdateEventModel).filter(
                UpdateEventModel.monster_state_db_id == monster_state.id
            ).delete()

            self.db.commit()

            logger.info(f"Deleted all update events for {monster_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete update events for {monster_id}: {e}")
            self.db.rollback()
            return False

    @staticmethod
    def _db_to_pydantic(event: UpdateEventModel) -> UpdateEvent:
        """Convertit un modèle DB en schéma Pydantic"""
        return UpdateEvent(
            id=int(event.id),  # type: ignore
            monster_state_db_id=int(event.monster_state_db_id),  # type: ignore
            occurred_at=event.occurred_at,  # type: ignore
            actor_type=str(event.actor_type),  # type: ignore
            actor_name=str(event.actor_name),  # type: ignore
            actor_id=str(event.actor_id) if event.actor_id else None,  # type: ignore
            source=str(event.source),  # type: ignore
            reason=str(event.reason) if event.reason else None,  # type: ignore
            validation_before=bool(event.validation_before),  # type: ignore
            validation_after=bool(event.validation_after),  # type: ignore
            skip_validation=bool(event.skip_validation),  # type: ignore
            storage_mode_before=str(event.storage_mode_before),  # type: ignore
            storage_mode_after=str(event.storage_mode_after),  # type: ignore
            changed_fields=list(event.changed_fields) if event.changed_fields else [],  # type: ignore
            diff_payload=dict(event.diff_payload) if event.diff_payload else None,  # type: ignore
            request_context=dict(event.request_context)
            if event.request_context
            else None,  # type: ignore
        )
