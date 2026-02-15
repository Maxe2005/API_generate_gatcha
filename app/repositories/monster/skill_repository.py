"""
Module: repositories.monster.skill_repository

Description:
Repository pour la gestion des compétences (Skill) via PostgreSQL.
Gère la persistance des skills associées aux monstres.
"""

from typing import Optional, List
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.monster import Skill, Monster
from app.schemas.skill import SkillCreate, SkillUpdate

logger = logging.getLogger(__name__)


class SkillRepository:
    """
    Gère la persistance des compétences (skills) via PostgreSQL.
    CRUD sur la table skills.
    """

    def __init__(self, db: Session):
        """
        Initialise le repository.

        Args:
            db: Session SQLAlchemy
        """
        self.db = db

    def create(self, monster_db_id: int, skill_data: SkillCreate) -> Optional[Skill]:
        """
        Crée une nouvelle compétence pour un monstre.

        Args:
            monster_db_id: ID du monstre
            skill_data: Données de la compétence

        Returns:
            Skill créée, None en cas d'erreur
        """
        try:
            # Vérifier que le monstre existe
            monster = self.db.query(Monster).filter(Monster.id == monster_db_id).first()
            if not monster:
                raise ValueError(f"Monster {monster_db_id} not found")

            skill = Skill(
                monster_id=monster_db_id,
                name=skill_data.name,
                description=skill_data.description,
                damage=skill_data.damage,
                cooldown=skill_data.cooldown,
                lvl_max=skill_data.lvl_max,
                rank=skill_data.rank,
                ratio_stat=skill_data.ratio_stat,
                ratio_percent=skill_data.ratio_percent,
            )
            self.db.add(skill)
            self.db.commit()
            self.db.refresh(skill)

            logger.info(f"Created skill {skill_data.name} for monster {monster_db_id}")
            return skill

        except Exception as e:
            logger.error(f"Failed to create skill for monster {monster_db_id}: {e}")
            self.db.rollback()
            return None

    def get_by_id(self, skill_id: int) -> Optional[Skill]:
        """
        Récupère une compétence par son ID.

        Args:
            skill_id: ID de la compétence

        Returns:
            Skill si trouvée, None sinon
        """
        try:
            return self.db.query(Skill).filter(Skill.id == skill_id).first()
        except Exception as e:
            logger.error(f"Failed to get skill {skill_id}: {e}")
            return None

    def get_by_monster(self, monster_db_id: int) -> List[Skill]:
        """
        Récupère toutes les compétences d'un monstre.

        Args:
            monster_db_id: ID du monstre

        Returns:
            Liste des compétences
        """
        try:
            return (
                self.db.query(Skill)
                .filter(Skill.monster_id == monster_db_id)
                .order_by(Skill.id)
                .all()
            )
        except Exception as e:
            logger.error(f"Failed to get skills for monster {monster_db_id}: {e}")
            return []

    def update(self, skill_id: int, updates: SkillUpdate) -> Optional[Skill]:
        """
        Met à jour une compétence.

        Args:
            skill_id: ID de la compétence
            updates: Données à mettre à jour

        Returns:
            Skill mise à jour, None en cas d'erreur
        """
        try:
            skill = self.db.query(Skill).filter(Skill.id == skill_id).first()
            if not skill:
                return None

            # Mettre à jour les champs fournis
            if updates.name is not None:
                skill.name = updates.name  # type: ignore
            if updates.description is not None:
                skill.description = updates.description  # type: ignore
            if updates.damage is not None:
                skill.damage = updates.damage  # type: ignore
            if updates.cooldown is not None:
                skill.cooldown = updates.cooldown  # type: ignore
            if updates.lvl_max is not None:
                skill.lvl_max = updates.lvl_max  # type: ignore
            if updates.rank is not None:
                skill.rank = updates.rank  # type: ignore
            if updates.ratio_stat is not None:
                skill.ratio_stat = updates.ratio_stat  # type: ignore
            if updates.ratio_percent is not None:
                skill.ratio_percent = updates.ratio_percent  # type: ignore

            skill.updated_at = datetime.now(timezone.utc)  # type: ignore
            self.db.commit()
            logger.info(f"Updated skill {skill_id}")

            return skill

        except Exception as e:
            logger.error(f"Failed to update skill {skill_id}: {e}")
            self.db.rollback()
            return None

    def delete(self, skill_id: int) -> bool:
        """
        Supprime une compétence.

        Args:
            skill_id: ID de la compétence

        Returns:
            True si succès, False sinon
        """
        try:
            skill = self.db.query(Skill).filter(Skill.id == skill_id).first()
            if not skill:
                return False

            self.db.delete(skill)
            self.db.commit()
            logger.info(f"Deleted skill {skill_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete skill {skill_id}: {e}")
            self.db.rollback()
            return False

    def delete_all_by_monster(self, monster_db_id: int) -> bool:
        """
        Supprime toutes les compétences d'un monstre.

        Args:
            monster_db_id: ID du monstre

        Returns:
            True si succès, False sinon
        """
        try:
            self.db.query(Skill).filter(Skill.monster_id == monster_db_id).delete()
            self.db.commit()
            logger.info(f"Deleted all skills for monster {monster_db_id}")

            return True

        except Exception as e:
            logger.error(
                f"Failed to delete all skills for monster {monster_db_id}: {e}"
            )
            self.db.rollback()
            return False
