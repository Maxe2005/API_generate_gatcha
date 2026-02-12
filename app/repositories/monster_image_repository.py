"""
Module: monster_image_repository

Description:
Gère la persistance des images de monstres via PostgreSQL.
"""

from typing import Optional, List
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.monster_image_model import MonsterImage

logger = logging.getLogger(__name__)


class MonsterImageRepository:
    """
    Gère la persistance des images de monstres via PostgreSQL.
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
        monster_db_id: int,
        image_name: str,
        image_url: str,
        prompt: str,
        is_default: bool = False,
        raw_image_key: Optional[str] = None,
    ) -> MonsterImage:
        """
        Crée une nouvelle image pour un monstre.

        Args:
            monster_db_id: ID de base de données du monstre
            image_name: Nom de l'image
            image_url: URL de l'image sur MinIO
            prompt: Prompt utilisé pour générer l'image
            is_default: Si c'est l'image par défaut
            raw_image_key: Clé d'objet de l'image 4K brute (usage interne)

        Returns:
            MonsterImage: L'image créée
        """
        # Si cette image est marquée comme défaut, retirer le flag des autres
        if is_default:
            self._unset_default_images(monster_db_id)

        new_image = MonsterImage(
            monster_id=monster_db_id,
            image_name=image_name,
            image_url=image_url,
            raw_image_key=raw_image_key,
            prompt=prompt,
            is_default=is_default,
        )
        self.db.add(new_image)
        self.db.commit()
        self.db.refresh(new_image)

        logger.info(
            f"Image créée: {image_name} pour le monstre ID {monster_db_id} (default={is_default})"
        )
        return new_image

    def get_images_by_monster_id(self, monster_db_id: int) -> List[MonsterImage]:
        """
        Récupère toutes les images d'un monstre.

        Args:
            monster_db_id: ID de base de données du monstre

        Returns:
            List[MonsterImage]: Liste des images
        """
        return (
            self.db.query(MonsterImage)
            .filter(MonsterImage.monster_id == monster_db_id)
            .order_by(MonsterImage.created_at.desc())
            .all()
        )

    def get_default_image(self, monster_db_id: int) -> Optional[MonsterImage]:
        """
        Récupère l'image par défaut d'un monstre.

        Args:
            monster_db_id: ID de base de données du monstre

        Returns:
            Optional[MonsterImage]: L'image par défaut ou None
        """
        return (
            self.db.query(MonsterImage)
            .filter(
                and_(
                    MonsterImage.monster_id == monster_db_id,
                    MonsterImage.is_default,
                )
            )
            .first()
        )

    def set_default_image(self, image_id: int, monster_db_id: int) -> MonsterImage:
        """
        Définit une image comme image par défaut pour un monstre.
        Retire le flag is_default des autres images.

        Args:
            image_id: ID de l'image à définir comme défaut
            monster_db_id: ID de base de données du monstre

        Returns:
            MonsterImage: L'image mise à jour

        Raises:
            ValueError: Si l'image n'existe pas ou n'appartient pas au monstre
        """
        # Vérifier que l'image existe et appartient au monstre
        image = self.db.query(MonsterImage).filter(MonsterImage.id == image_id).first()
        if not image:
            raise ValueError(f"Image avec ID {image_id} non trouvée")
        # Note: La comparaison directe avec SQLAlchemy Column ne fonctionne pas bien avec les types
        # On récupère la valeur de la colonne pour la comparer
        if int(image.monster_id) != int(monster_db_id):  # type: ignore
            raise ValueError(
                f"L'image {image_id} n'appartient pas au monstre {monster_db_id}"
            )

        # Retirer le flag des autres images
        self._unset_default_images(monster_db_id)

        # Définir cette image comme défaut
        image.is_default = True  # type: ignore
        self.db.commit()
        self.db.refresh(image)

        logger.info(
            f"Image {image_id} définie comme défaut pour le monstre {monster_db_id}"
        )
        return image

    def _unset_default_images(self, monster_db_id: int) -> None:
        """
        Retire le flag is_default de toutes les images d'un monstre.

        Args:
            monster_db_id: ID de base de données du monstre
        """
        self.db.query(MonsterImage).filter(
            and_(MonsterImage.monster_id == monster_db_id, MonsterImage.is_default)
        ).update({"is_default": False})
        self.db.commit()

    def get_image_by_id(self, image_id: int) -> Optional[MonsterImage]:
        """
        Récupère une image par son ID.

        Args:
            image_id: ID de l'image

        Returns:
            Optional[MonsterImage]: L'image ou None
        """
        return self.db.query(MonsterImage).filter(MonsterImage.id == image_id).first()

    def delete_image(self, image_id: int) -> bool:
        """
        Supprime une image.

        Args:
            image_id: ID de l'image à supprimer

        Returns:
            bool: True si l'image a été supprimée, False sinon
        """
        image = self.get_image_by_id(image_id)
        if not image:
            return False

        self.db.delete(image)
        self.db.commit()
        logger.info(f"Image {image_id} supprimée")
        return True
