"""
Module: skill_image_repository

Description:
Gère la persistance des cartes de compétence via PostgreSQL. Miroir de
MonsterImageRepository, mais scopé par (skill_id, source_monster_image_id) :
une compétence peut avoir plusieurs groupes de cartes, un par image de
monstre utilisée comme référence, et is_default n'est unique qu'au sein
d'un même groupe.
"""

from typing import Optional, List
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.monster.skill_image import SkillImage

logger = logging.getLogger(__name__)


class SkillImageRepository:
    """
    Gère la persistance des cartes de compétence via PostgreSQL.
    """

    def __init__(self, db: Session):
        """
        Initialise le repository avec une session de base de données.

        Args:
            db: Session SQLAlchemy
        """
        self.db = db

    def create_image(
        self,
        skill_id: int,
        source_monster_image_id: int,
        image_url: str,
        prompt: str,
        provider: str,
        model: Optional[str] = None,
        is_default: bool = False,
        raw_image_key: Optional[str] = None,
    ) -> SkillImage:
        """
        Crée une nouvelle carte de compétence.

        Args:
            skill_id: ID de la compétence
            source_monster_image_id: ID de l'image de monstre utilisée comme référence
            image_url: URL de l'image sur MinIO
            prompt: Prompt utilisé pour générer l'image
            provider: Provider IA utilisé (fal, gemini)
            model: Modèle utilisé pour la génération
            is_default: Si c'est l'image par défaut du groupe (skill_id, source_monster_image_id)
            raw_image_key: Clé d'objet de l'image 4K brute (usage interne)

        Returns:
            SkillImage: La carte créée
        """
        if is_default:
            self._unset_default_images(skill_id, source_monster_image_id)

        new_image = SkillImage(
            skill_id=skill_id,
            source_monster_image_id=source_monster_image_id,
            image_url=image_url,
            raw_image_key=raw_image_key,
            prompt=prompt,
            provider=provider,
            model=model,
            is_default=is_default,
        )
        self.db.add(new_image)
        self.db.commit()
        self.db.refresh(new_image)

        logger.info(
            f"Carte de compétence créée pour skill ID {skill_id} "
            f"(source_monster_image_id={source_monster_image_id}, default={is_default})"
        )
        return new_image

    def get_images_by_skill_and_source(
        self, skill_id: int, source_monster_image_id: int
    ) -> List[SkillImage]:
        """
        Récupère toutes les cartes de compétence d'un groupe
        (skill_id, source_monster_image_id).
        """
        return (
            self.db.query(SkillImage)
            .filter(
                and_(
                    SkillImage.skill_id == skill_id,
                    SkillImage.source_monster_image_id == source_monster_image_id,
                )
            )
            .order_by(SkillImage.created_at.desc())
            .all()
        )

    def get_default_image_for_source(
        self, skill_id: int, source_monster_image_id: int
    ) -> Optional[SkillImage]:
        """Récupère la carte par défaut d'un groupe (skill_id, source_monster_image_id)."""
        return (
            self.db.query(SkillImage)
            .filter(
                and_(
                    SkillImage.skill_id == skill_id,
                    SkillImage.source_monster_image_id == source_monster_image_id,
                    SkillImage.is_default,
                )
            )
            .first()
        )

    def set_default_image(self, image_id: int, skill_id: int) -> SkillImage:
        """
        Définit une carte comme carte par défaut au sein de son groupe
        (skill_id, source_monster_image_id).

        Raises:
            ValueError: Si la carte n'existe pas ou n'appartient pas à la compétence
        """
        image = self.db.query(SkillImage).filter(SkillImage.id == image_id).first()
        if not image:
            raise ValueError(f"Carte de compétence avec ID {image_id} non trouvée")
        if int(image.skill_id) != int(skill_id):  # type: ignore
            raise ValueError(f"La carte {image_id} n'appartient pas à la compétence {skill_id}")

        self._unset_default_images(skill_id, int(image.source_monster_image_id))  # type: ignore

        image.is_default = True  # type: ignore
        self.db.commit()
        self.db.refresh(image)

        logger.info(f"Carte {image_id} définie comme défaut pour la compétence {skill_id}")
        return image

    def _unset_default_images(self, skill_id: int, source_monster_image_id: int) -> None:
        """Retire le flag is_default de toutes les cartes du groupe donné."""
        self.db.query(SkillImage).filter(
            and_(
                SkillImage.skill_id == skill_id,
                SkillImage.source_monster_image_id == source_monster_image_id,
                SkillImage.is_default,
            )
        ).update({"is_default": False})
        self.db.commit()

    def get_image_by_id(self, image_id: int) -> Optional[SkillImage]:
        """Récupère une carte de compétence par son ID."""
        return self.db.query(SkillImage).filter(SkillImage.id == image_id).first()

    def delete_image(self, image_id: int) -> bool:
        """Supprime une carte de compétence."""
        image = self.get_image_by_id(image_id)
        if not image:
            return False

        self.db.delete(image)
        self.db.commit()
        logger.info(f"Carte de compétence {image_id} supprimée")
        return True
