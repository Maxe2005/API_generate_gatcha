"""
Module: repositories.monster.structure_repository

Description:
Repository pour gèrer les transitions et en particulier celle vers PENDING_REVIEW.
Crée des monstres structurés à partir de JSON.
Gère la transition JSON → Monster structuré + Skills.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging

from sqlalchemy.orm import Session

from app.core.constants import MonsterStateEnum
from app.models.monster import Monster, Skill, MonsterState
from app.models.monster.transition import StateTransitionModel
from app.models.monster_image_model import MonsterImage

from app.core.json_monster_config import (
    MonsterJsonAttributes,
    MonsterJsonStatsAttributes,
    MonsterJsonSkillAttributes,
    MonsterJsonSkillRatioAttributes,
)

logger = logging.getLogger(__name__)


class TransitionRepository:
    """
    Crée des monstres structurés à partir de données JSON.
    Utilisé lors de la transition vers PENDING_REVIEW.
    """

    def __init__(self, db: Session):
        """
        Initialise le repository.

        Args:
            db: Session SQLAlchemy
        """
        self.db = db

    def create_structured_monster_from_json(
        self, monster_state: MonsterState, monster_json: Dict[str, Any]
    ) -> Optional[Monster]:
        """
        Crée un monstre structuré et ses skills à partir du JSON.
        Utilisé lors de la transition vers PENDING_REVIEW.

        Args:
            monster_state: MonsterState DB object
            monster_json: Données JSON du monstre

        Returns:
            Monster créé ou None en cas d'erreur
        """
        try:
            # Créer le monstre structuré
            monster = Monster(
                monster_state_id=monster_state.id,
                nom=monster_json[MonsterJsonAttributes.NAME.value],
                element=monster_json[MonsterJsonAttributes.ELEMENT.value],
                rang=monster_json[MonsterJsonAttributes.RANK.value],
                hp=monster_json[MonsterJsonAttributes.STATS.value][
                    MonsterJsonStatsAttributes.HP.value
                ],
                atk=monster_json[MonsterJsonAttributes.STATS.value][
                    MonsterJsonStatsAttributes.ATK.value
                ],
                def_=monster_json[MonsterJsonAttributes.STATS.value][
                    MonsterJsonStatsAttributes.DEF.value
                ],
                vit=monster_json[MonsterJsonAttributes.STATS.value][
                    MonsterJsonStatsAttributes.VIT.value
                ],
                description_carte=monster_json[
                    MonsterJsonAttributes.DESCRIPTION_CARD.value
                ],
                description_visuelle=monster_json[
                    MonsterJsonAttributes.DESCRIPTION_VISUAL.value
                ],
            )

            self.db.add(monster)
            self.db.flush()  # Pour obtenir l'ID du monstre

            # Créer les skills
            for skill_data in monster_json[MonsterJsonAttributes.SKILLS.value]:
                skill = Skill(
                    monster_id=monster.id,
                    name=skill_data[MonsterJsonSkillAttributes.NAME.value],
                    description=skill_data[
                        MonsterJsonSkillAttributes.DESCRIPTION.value
                    ],
                    damage=skill_data[MonsterJsonSkillAttributes.DAMAGE.value],
                    cooldown=skill_data[MonsterJsonSkillAttributes.COOLDOWN.value],
                    lvl_max=skill_data[MonsterJsonSkillAttributes.LVL_MAX.value],
                    rank=skill_data[MonsterJsonSkillAttributes.RANK.value],
                    ratio_stat=skill_data[MonsterJsonSkillAttributes.RATIO.value][
                        MonsterJsonSkillRatioAttributes.STAT.value
                    ],
                    ratio_percent=skill_data[MonsterJsonSkillAttributes.RATIO.value][
                        MonsterJsonSkillRatioAttributes.PERCENT.value
                    ],
                )
                self.db.add(skill)

            # Create default image entry in monster_images table
            image_name = monster.nom
            image_url: str = monster_json[MonsterJsonAttributes.IMAGE_URL.value]
            raw_image_key = image_url  # .replace("", "")  # TODO Extract raw image key from URL if needed
            image = MonsterImage(
                monster_id=monster.id,
                image_name=image_name,
                image_url=image_url,
                raw_image_key=raw_image_key,
                prompt=monster.description_visuelle,
                is_default=True,
                created_at=monster_state.created_at,  # Use the same timestamp as the monster state
            )
            self.db.add(image)

            # Mettre monster_data à NULL
            monster_state.monster_data = None  # type: ignore

            self.db.commit()
            self.db.refresh(monster)

            logger.info(
                f"Created structured monster from JSON for {monster_state.monster_id}"
            )
            return monster

        except Exception as e:
            logger.error(
                f"Failed to create structured monster from JSON for {monster_state.monster_id}: {e}"
            )
            self.db.rollback()
            return None

    def add_transition(
        self,
        monster_id: str,
        from_state: Optional[MonsterStateEnum],
        to_state: MonsterStateEnum,
        actor: str,
        note: Optional[str] = None,
    ) -> bool:
        """Ajoute une transition d'état à l'historique"""
        try:
            db_monster_state = (
                self.db.query(MonsterState)
                .filter(MonsterState.monster_id == monster_id)
                .first()
            )

            if not db_monster_state:
                return False

            transition = StateTransitionModel(
                monster_state_db_id=db_monster_state.id,
                from_state=(MonsterStateEnum(from_state.value) if from_state else None),
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

    def move_to_state(
        self,
        monster_id: str,
        new_state: MonsterStateEnum,
        actor: str = "system",
        note: Optional[str] = None,
    ) -> bool:
        """Change l'état d'un monstre"""
        try:
            db_monster_state = (
                self.db.query(MonsterState)
                .filter(MonsterState.monster_id == monster_id)
                .first()
            )

            if not db_monster_state:
                return False

            old_state = db_monster_state.state
            db_monster_state.state = new_state  # type: ignore
            db_monster_state.updated_at = datetime.now(timezone.utc)  # type: ignore

            # Créer la transition via add_transition pour la cohérence
            transition_note = (
                note or f"State changed from {old_state.value} to {new_state.value}"
            )
            transition = StateTransitionModel(
                monster_state_db_id=db_monster_state.id,
                from_state=old_state,
                to_state=new_state,
                actor=actor,
                note=transition_note,
            )
            self.db.add(transition)

            self.db.commit()

            if new_state == MonsterStateEnum.PENDING_REVIEW:
                self.create_structured_monster_from_json(
                    db_monster_state,
                    db_monster_state.monster_data,  # type: ignore
                )
            logger.info(f"Moved monster {monster_id} to state {new_state} by {actor}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to move monster {monster_id} to state {new_state}: {e}"
            )
            self.db.rollback()
            return False
