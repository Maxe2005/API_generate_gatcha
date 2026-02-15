"""
Module: repositories.monster.repository

Description:
Repository pour la gestion des monstres structurés (Monster) via PostgreSQL.
Gère la persistance des données structurées des monstres.
"""

from typing import Optional
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.monster import Monster
from app.schemas.monster import MonsterUpdate

logger = logging.getLogger(__name__)


class MonsterRepository:
    """
    Gère la persistance des monstres structurés via PostgreSQL.
    CRUD sur la table monsters et les relations associées.
    """

    def __init__(self, db: Session):
        """
        Initialise le repository.

        Args:
            db: Session SQLAlchemy
        """
        self.db = db

    def get_by_id(self, monster_db_id: int) -> Optional[Monster]:
        """
        Récupère un monstre par son ID de base de données.

        Args:
            monster_db_id: ID de la base de données

        Returns:
            Monster si trouvé, None sinon
        """
        try:
            return self.db.query(Monster).filter(Monster.id == monster_db_id).first()
        except Exception as e:
            logger.error(f"Failed to get monster by ID {monster_db_id}: {e}")
            return None
    
    def get_by_uuid(self, monster_uuid: str) -> Optional[Monster]:
        """
        Récupère un monstre par son UUID.

        Args:
            monster_uuid: UUID du monstre

        Returns:
            Monster si trouvé, None sinon
        """
        try:
            return (
                self.db.query(Monster)
                .filter(Monster.monster_uuid == monster_uuid)
                .first()
            )
        except Exception as e:
            logger.error(f"Failed to get monster by UUID {monster_uuid}: {e}")
            return None

    def get_by_monster_state_id(self, monster_state_id: int) -> Optional[Monster]:
        """
        Récupère un monstre par l'ID de son MonsterState.

        Args:
            monster_state_id: ID du MonsterState

        Returns:
            Monster si trouvé, None sinon
        """
        try:
            return (
                self.db.query(Monster)
                .filter(Monster.monster_state_id == monster_state_id)
                .first()
            )
        except Exception as e:
            logger.error(
                f"Failed to get monster by monster_state_id {monster_state_id}: {e}"
            )
            return None
    
    def get_all(self) -> list[Monster]:
        """
        Récupère tous les monstres.

        Returns:
            Liste de tous les monstres
        """
        try:
            return self.db.query(Monster).all()
        except Exception as e:
            logger.error(f"Failed to get all monsters: {e}")
            return []

    def update(self, monster_db_id: int, updates: MonsterUpdate) -> Optional[Monster]:
        """
        Met à jour un monstre.

        Args:
            monster_db_id: ID de base de données du monstre
            updates: Données à mettre à jour

        Returns:
            Monster mis à jour, None en cas d'erreur
        """
        try:
            monster = self.db.query(Monster).filter(Monster.id == monster_db_id).first()
            if not monster:
                return None

            # Mettre à jour les champs fournis
            if updates.nom is not None:
                monster.nom = updates.nom  # type: ignore
            if updates.element is not None:
                monster.element = updates.element  # type: ignore
            if updates.rang is not None:
                monster.rang = updates.rang  # type: ignore
            if updates.hp is not None:
                monster.hp = updates.hp  # type: ignore
            if updates.atk is not None:
                monster.atk = updates.atk  # type: ignore
            if updates.def_ is not None:
                monster.def_ = updates.def_  # type: ignore
            if updates.vit is not None:
                monster.vit = updates.vit  # type: ignore
            if updates.description_carte is not None:
                monster.description_carte = updates.description_carte  # type: ignore
            if updates.description_visuelle is not None:
                monster.description_visuelle = updates.description_visuelle  # type: ignore

            monster.updated_at = datetime.now(timezone.utc)  # type: ignore
            self.db.commit()
            logger.info(f"Updated monster {monster_db_id}")

            return monster

        except Exception as e:
            logger.error(f"Failed to update monster {monster_db_id}: {e}")
            self.db.rollback()
            return None

    def delete(self, monster_db_id: int) -> bool:
        """
        Supprime un monstre (cascade sur Skill et MonsterImage).

        Args:
            monster_db_id: ID de base de données du monstre

        Returns:
            True si succès, False sinon
        """
        try:
            monster = self.db.query(Monster).filter(Monster.id == monster_db_id).first()
            if not monster:
                return False

            self.db.delete(monster)
            self.db.commit()
            logger.info(f"Deleted monster {monster_db_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete monster {monster_db_id}: {e}")
            self.db.rollback()
            return False
