"""
Module: monster_repository

Description:
Gère la persistance des monstres et de leurs métadonnées via PostgreSQL.
"""

from typing import Optional, List, Dict, Any
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.schemas.metadata import MonsterMetadata, MonsterWithMetadata, StateTransition
from app.schemas.monster import MonsterState
from app.models.monster_model import Monster, StateTransitionModel, MonsterStateEnum

logger = logging.getLogger(__name__)


class MonsterRepository:
    """
    Gère la persistance des monstres et de leurs métadonnées via PostgreSQL.
    """

    def __init__(self, db: Session):
        """
        Initialise le repository avec une session de base de données.

        Args:
            db: Session SQLAlchemy
        """
        self.db = db

    def _db_to_metadata(self, db_monster: Monster) -> MonsterMetadata:  # pyright: ignore
        """Convertit un modèle DB en MonsterMetadata Pydantic"""
        # Convertir les transitions d'état
        history = [
            StateTransition(
                from_state=MonsterState(t.from_state.value) if t.from_state else None,
                to_state=MonsterState(t.to_state.value),
                timestamp=t.timestamp,
                actor=t.actor,
                note=t.note,
            )
            for t in db_monster.history
        ]

        return MonsterMetadata(
            monster_id=db_monster.monster_id,  # type: ignore
            state=MonsterState(db_monster.state.value),
            created_at=db_monster.created_at,  # type: ignore
            updated_at=db_monster.updated_at,  # type: ignore
            generated_by=db_monster.generated_by,  # type: ignore
            generation_prompt=db_monster.generation_prompt,  # type: ignore
            is_valid=db_monster.is_valid,  # type: ignore
            validation_errors=db_monster.validation_errors,  # type: ignore
            reviewed_by=db_monster.reviewed_by,  # type: ignore
            review_date=db_monster.review_date,  # type: ignore
            review_notes=db_monster.review_notes,  # type: ignore
            transmitted_at=db_monster.transmitted_at,  # type: ignore
            transmission_attempts=db_monster.transmission_attempts,  # type: ignore
            last_transmission_error=db_monster.last_transmission_error,  # type: ignore
            invocation_api_id=db_monster.invocation_api_id,  # type: ignore
            history=history,
        )

    def save(self, metadata: MonsterMetadata, monster_data: Dict[str, Any]) -> bool:
        """
        Sauvegarde un monstre et ses métadonnées.

        Args:
            metadata: Métadonnées du monstre
            monster_data: Données du monstre (nom, stats, skills, etc.)

        Returns:
            True si succès
        """
        try:
            # Vérifier si le monstre existe déjà
            existing = (
                self.db.query(Monster)
                .filter(Monster.monster_id == metadata.monster_id)
                .first()
            )

            if existing:  # type: ignore
                # Mise à jour
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
                existing.updated_at = datetime.now()  # type: ignore

                logger.info(f"Updated monster {metadata.monster_id}")
            else:
                # Création
                db_monster = Monster(  # type: ignore
                    monster_id=metadata.monster_id,
                    state=MonsterStateEnum(metadata.state.value),
                    monster_data=monster_data,  # type: ignore
                    generated_by=metadata.generated_by,
                    generation_prompt=metadata.generation_prompt,
                    is_valid=metadata.is_valid,
                    validation_errors=metadata.validation_errors,  # type: ignore
                    reviewed_by=metadata.reviewed_by,
                    review_date=metadata.review_date,
                    review_notes=metadata.review_notes,
                    transmitted_at=metadata.transmitted_at,
                    transmission_attempts=metadata.transmission_attempts,
                    last_transmission_error=metadata.last_transmission_error,
                    invocation_api_id=metadata.invocation_api_id,
                )
                self.db.add(db_monster)
                logger.info(f"Created monster {metadata.monster_id}")

            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to save monster {metadata.monster_id}: {e}")
            self.db.rollback()
            return False

    def get(self, monster_id: str) -> Optional[MonsterWithMetadata]:
        """Récupère un monstre avec ses métadonnées"""
        try:
            db_monster = (
                self.db.query(Monster).filter(Monster.monster_id == monster_id).first()
            )

            if not db_monster:
                return None

            metadata = self._db_to_metadata(db_monster)

            return MonsterWithMetadata(
                metadata=metadata,
                monster_data=db_monster.monster_data,  # type: ignore
            )

        except Exception as e:
            logger.error(f"Failed to get monster {monster_id}: {e}")
            return None

    def get_db_monster(self, monster_id: str) -> Optional[Monster]:
        """Récupère l'objet DB Monster directement"""
        try:
            return (
                self.db.query(Monster).filter(Monster.monster_id == monster_id).first()
            )
        except Exception as e:
            logger.error(f"Failed to get DB monster {monster_id}: {e}")
            return None

    def list_by_state(
        self, state: MonsterState, limit: int = 50, offset: int = 0
    ) -> List[MonsterMetadata]:
        """Liste les monstres par état"""
        try:
            db_monsters = (
                self.db.query(Monster)
                .filter(Monster.state == MonsterStateEnum(state.value))
                .order_by(Monster.updated_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            return [self._db_to_metadata(m) for m in db_monsters]

        except Exception as e:
            logger.error(f"Failed to list monsters by state {state}: {e}")
            return []

    def list_all(self, limit: int = 50, offset: int = 0) -> List[MonsterMetadata]:
        """Liste tous les monstres"""
        try:
            db_monsters = (
                self.db.query(Monster)
                .order_by(Monster.updated_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            return [self._db_to_metadata(m) for m in db_monsters]

        except Exception as e:
            logger.error(f"Failed to list all monsters: {e}")
            return []

    def move_to_state(self, monster_id: str, new_state: MonsterState) -> bool:
        """Change l'état d'un monstre"""
        try:
            db_monster = (
                self.db.query(Monster).filter(Monster.monster_id == monster_id).first()
            )

            if not db_monster:
                return False

            old_state = db_monster.state
            db_monster.state = MonsterStateEnum(new_state.value)  # type: ignore
            db_monster.updated_at = datetime.now()  # type: ignore

            # Ajouter une transition dans l'historique
            transition = StateTransitionModel(
                monster_db_id=db_monster.id,
                from_state=old_state,
                to_state=MonsterStateEnum(new_state.value),
                actor="system",
                note=f"State changed from {old_state.value} to {new_state.value}",
            )
            self.db.add(transition)

            self.db.commit()
            logger.info(f"Moved monster {monster_id} to state {new_state}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to move monster {monster_id} to state {new_state}: {e}"
            )
            self.db.rollback()
            return False

    def delete(self, monster_id: str) -> bool:
        """Supprime un monstre et ses métadonnées"""
        try:
            db_monster = (
                self.db.query(Monster).filter(Monster.monster_id == monster_id).first()
            )

            if not db_monster:
                return False

            self.db.delete(db_monster)
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
                self.db.query(Monster.state, func.count(Monster.id))
                .group_by(Monster.state)
                .all()
            )

            counts = {state.value: 0 for state in MonsterState}
            for state_enum, count in results:
                counts[state_enum.value] = count

            return counts

        except Exception as e:
            logger.error(f"Failed to count by state: {e}")
            return {state.value: 0 for state in MonsterState}

    def add_transition(
        self,
        monster_id: str,
        from_state: Optional[MonsterState],
        to_state: MonsterState,
        actor: str,
        note: Optional[str] = None,
    ) -> bool:
        """Ajoute une transition d'état à l'historique"""
        try:
            db_monster = (
                self.db.query(Monster).filter(Monster.monster_id == monster_id).first()
            )

            if not db_monster:
                return False

            transition = StateTransitionModel(
                monster_db_id=db_monster.id,
                from_state=MonsterStateEnum(from_state.value) if from_state else None,
                to_state=MonsterStateEnum(to_state.value),
                actor=actor,
                note=note,
            )
            self.db.add(transition)
            self.db.commit()

            return True

        except Exception as e:
            logger.error(f"Failed to add transition for monster {monster_id}: {e}")
            self.db.rollback()
            return False
