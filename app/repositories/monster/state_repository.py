"""
Module: repositories.monster.state_repository

Description:
Repository pour la gestion des états et métadonnées (MonsterState) via PostgreSQL.
Gère la persistance de l'état du cycle de vie des monstres.
"""

from typing import Optional, List, Dict
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import func, true

from app.models.monster import MonsterState
from app.schemas.admin import MonsterListFilter
from app.schemas.metadata import MonsterMetadata, MonsterWithMetadata, StateTransition
from app.core.constants import MonsterStateEnum

logger = logging.getLogger(__name__)


class MonsterStateRepository:
    """
    Gère la persistance des états et métadonnées des monstres via PostgreSQL.
    Gère les transitions d'état et l'historique.
    """

    def __init__(self, db: Session):
        """
        Initialise le repository.

        Args:
            db: Session SQLAlchemy
        """
        self.db = db

    def _db_to_metadata(self, db_monster_state: MonsterState) -> MonsterMetadata:
        """Convertit un modèle DB MonsterState en Pydantic MonsterMetadata"""
        history = [
            StateTransition(
                from_state=(  # type: ignore
                    MonsterStateEnum(t.from_state.value) if t.from_state else None
                ),
                to_state=MonsterStateEnum(t.to_state.value),  # type: ignore
                timestamp=t.timestamp,  # type: ignore
                actor=t.actor,  # type: ignore
                note=t.note,  # type: ignore
            )
            for t in db_monster_state.history
        ]

        return MonsterMetadata(
            monster_id=db_monster_state.monster_id,  # type: ignore
            state=MonsterStateEnum(db_monster_state.state.value),  # type: ignore
            created_at=db_monster_state.created_at,  # type: ignore
            updated_at=db_monster_state.updated_at,  # type: ignore
            generated_by=db_monster_state.generated_by,  # type: ignore
            generation_prompt=db_monster_state.generation_prompt,  # type: ignore
            is_valid=db_monster_state.is_valid,  # type: ignore
            validation_errors=db_monster_state.validation_errors,  # type: ignore
            reviewed_by=db_monster_state.reviewed_by,  # type: ignore
            review_date=db_monster_state.review_date,  # type: ignore
            review_notes=db_monster_state.review_notes,  # type: ignore
            transmitted_at=db_monster_state.transmitted_at,  # type: ignore
            transmission_attempts=db_monster_state.transmission_attempts,  # type: ignore
            last_transmission_error=db_monster_state.last_transmission_error,  # type: ignore
            invocation_api_id=db_monster_state.invocation_api_id,  # type: ignore
            history=history,
            monster=db_monster_state.monster is not None,  # type: ignore
        )

    def save(
        self, metadata: MonsterMetadata, monster_data: Optional[Dict] = None
    ) -> bool:
        """
        Sauvegarde/met à jour un état de monstre et ses métadonnées.

        Args:
            metadata: Métadonnées
            monster_data: Données JSON du monstre (peut etre None)

        Returns:
            True si succès
        """
        try:
            existing = (
                self.db.query(MonsterState)
                .filter(MonsterState.monster_id == metadata.monster_id)
                .first()
            )

            if existing:
                existing.state = MonsterStateEnum(metadata.state.value)  # type: ignore
                existing.monster_data = monster_data  # type: ignore
                existing.generated_by = metadata.generated_by  # type: ignore
                existing.generation_prompt = metadata.generation_prompt  # type: ignore
                existing.is_valid = metadata.is_valid  # type: ignore
                existing.validation_errors = metadata.validation_errors  # type: ignore
                existing.reviewed_by = metadata.reviewed_by  # type: ignore
                existing.review_date = metadata.review_date  # type: ignore
                existing.review_notes = metadata.review_notes  # type: ignore
                existing.transmitted_at = metadata.transmitted_at  # type: ignore
                existing.transmission_attempts = metadata.transmission_attempts  # type: ignore
                existing.last_transmission_error = metadata.last_transmission_error  # type: ignore
                existing.invocation_api_id = metadata.invocation_api_id  # type: ignore
                existing.updated_at = datetime.now(timezone.utc)  # type: ignore

                logger.info(f"Updated monster state {metadata.monster_id}")
            else:
                db_monster_state = MonsterState(
                    monster_id=metadata.monster_id,
                    state=MonsterStateEnum(metadata.state.value),
                    monster_data=monster_data,
                    generated_by=metadata.generated_by,
                    generation_prompt=metadata.generation_prompt,
                    is_valid=metadata.is_valid,
                    validation_errors=metadata.validation_errors,
                    reviewed_by=metadata.reviewed_by,
                    review_date=metadata.review_date,
                    review_notes=metadata.review_notes,
                    transmitted_at=metadata.transmitted_at,
                    transmission_attempts=metadata.transmission_attempts,
                    last_transmission_error=metadata.last_transmission_error,
                    invocation_api_id=metadata.invocation_api_id,
                )
                self.db.add(db_monster_state)
                logger.info(f"Created monster state {metadata.monster_id}")

            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to save monster state {metadata.monster_id}: {e}")
            self.db.rollback()
            return False

    def get(self, monster_id: str) -> Optional[MonsterWithMetadata]:
        """Récupère un monstre avec ses métadonnées"""
        try:
            db_monster_state = (
                self.db.query(MonsterState)
                .filter(MonsterState.monster_id == monster_id)
                .first()
            )

            if not db_monster_state:
                return None

            metadata = self._db_to_metadata(db_monster_state)

            return MonsterWithMetadata(
                metadata=metadata,
                monster_data=db_monster_state.monster_data,  # type: ignore
            )

        except Exception as e:
            logger.error(f"Failed to get monster {monster_id}: {e}")
            return None

    def list_filtred(self, filter: MonsterListFilter) -> List[MonsterMetadata]:
        """Liste les monstres par état"""
        try:
            db_monster_states = (
                self.db.query(MonsterState)
                .filter(
                    MonsterState.state == MonsterStateEnum(filter.state.value)
                    if filter.state
                    else true()
                )
                .filter(
                    MonsterState.is_valid == filter.is_valid
                    if filter.is_valid is not None
                    else true()
                )
                .order_by(
                    getattr(MonsterState, filter.sort_by).desc()
                    if filter.order == "desc"
                    else getattr(MonsterState, filter.sort_by).asc()
                )
                .limit(filter.limit)
                .offset(filter.offset)
                .all()
            )

            return [self._db_to_metadata(m) for m in db_monster_states]

        except Exception as e:
            logger.error(f"Failed to list monsters with the filter {filter}: {e}")
            return []

    def list_all(self, limit: int = 50, offset: int = 0) -> List[MonsterMetadata]:
        """Liste tous les monstres"""
        try:
            db_monster_states = (
                self.db.query(MonsterState)
                .order_by(MonsterState.updated_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            return [self._db_to_metadata(m) for m in db_monster_states]

        except Exception as e:
            logger.error(f"Failed to list all monsters: {e}")
            return []

    def delete(self, monster_id: str) -> bool:
        """Supprime un monstre et ses métadonnées"""
        try:
            db_monster_state = (
                self.db.query(MonsterState)
                .filter(MonsterState.monster_id == monster_id)
                .first()
            )

            if not db_monster_state:
                return False

            self.db.delete(db_monster_state)
            self.db.commit()

            logger.info(f"Deleted monster {monster_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete monster {monster_id}: {e}")
            self.db.rollback()
            return False

    def count_by_state(self) -> Dict[str, int]:
        """Compte les monstres par état"""
        try:
            results = (
                self.db.query(MonsterState.state, func.count(MonsterState.id))
                .group_by(MonsterState.state)
                .all()
            )

            counts = {state.value: 0 for state in MonsterStateEnum}
            for state_enum, count in results:
                counts[state_enum.value] = count

            return counts

        except Exception as e:
            logger.error(f"Failed to count by state: {e}")
            return {state.value: 0 for state in MonsterStateEnum}
