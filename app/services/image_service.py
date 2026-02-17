"""
Module: image_service

Description:
Service pour gérer la génération et la gestion des images de monstres
"""

import logging
from sqlalchemy.orm import Session

from app.repositories.monster_image_repository import MonsterImageRepository
from app.repositories.monster import MonsterRepository
from app.services.monster_modification_service import MonsterModificationService
from app.clients.banana import BananaClient
from app.schemas.image import MonsterImageResponse, MonsterImageListResponse

logger = logging.getLogger(__name__)


class ImageService:
    """
    Service pour gérer la génération et la gestion des images de monstres.
    """

    def __init__(self, db: Session, banana_client: BananaClient):
        """
        Initialise le service.

        Args:
            db: Session de base de données
            banana_client: Client pour la génération d'images
        """
        self.db = db
        self.image_repo = MonsterImageRepository(db)
        self.monster_repo = MonsterRepository(db)
        self.monster_mod_service = MonsterModificationService(db)
        self.banana_client = banana_client

    async def create_default_image_for_monster(
        self, monster_db_id: int, description_visuelle: str, monster_name: str
    ) -> MonsterImageResponse:
        """
        Crée l'image par défaut pour un monstre lors de sa génération.

        Args:
            monster_db_id: ID de base de données du monstre
            description_visuelle: Description visuelle du monstre
            monster_name: Nom du monstre

        Returns:
            MonsterImageResponse: L'image créée

        Raises:
            Exception: En cas d'erreur de génération ou de stockage
        """
        logger.info(
            f"Génération de l'image par défaut pour le monstre {monster_name} (ID: {monster_db_id})"
        )

        # Générer l'image via BananaClient (qui gère aussi l'upload MinIO)
        image_name = f"{monster_name.lower().replace(' ', '_')}_default"
        result = await self.banana_client.generate_pixel_art(
            description_visuelle, image_name
        )

        # Sauvegarder dans la base de données
        db_image = self.image_repo.create_image(
            monster_db_id=monster_db_id,
            image_name=image_name,
            image_url=result["image_url"],
            raw_image_key=result["raw_image_key"],
            prompt=description_visuelle,
            is_default=True,
        )

        return MonsterImageResponse.model_validate(db_image)

    async def create_custom_image_for_monster(
        self, monster_id: str, image_name: str, custom_prompt: str
    ) -> MonsterImageResponse:
        """
        Crée une nouvelle image personnalisée pour un monstre existant.

        Args:
            monster_id: ID de base de données du monstre
            image_name: Nom de l'image à créer
            custom_prompt: Prompt personnalisé (sera injecté dans IMAGE_GENERATION)

        Returns:
            MonsterImageResponse: L'image créée

        Raises:
            ValueError: Si le monstre n'existe pas
            Exception: En cas d'erreur de génération ou de stockage
        """
        # Récupérer le monstre
        monster = self.monster_repo.get_by_id(monster_id)
        if not monster:
            raise ValueError(f"Monstre avec ID {monster_id} non trouvé")

        logger.info(
            f"Génération d'une image personnalisée '{image_name}' pour le monstre {monster_id}"
        )

        # Générer l'image via BananaClient (qui gère aussi l'upload MinIO)
        safe_image_name = image_name.lower().replace(" ", "_")
        result = await self.banana_client.generate_pixel_art(
            custom_prompt, safe_image_name
        )
        image_url = result["image_url"]
        raw_image_key = result["raw_image_key"]

        # Sauvegarder dans la base de données
        db_image = self.image_repo.create_image(
            monster_db_id=int(monster.id),  # type: ignore
            image_name=safe_image_name,
            image_url=image_url,
            raw_image_key=raw_image_key,
            prompt=custom_prompt,
            is_default=False,
        )

        return MonsterImageResponse.model_validate(db_image)

    def get_monster_images(self, monster_id: int) -> MonsterImageListResponse:
        """
        Récupère toutes les images d'un monstre.

        Args:
            monster_id: ID de base de données du monstre

        Returns:
            MonsterImageListResponse: Liste des images avec l'image par défaut

        Raises:
            ValueError: Si le monstre n'existe pas
        """
        # Récupérer le monstre
        monster = self.monster_repo.get_by_id(monster_id)
        if not monster:
            raise ValueError(f"Monstre avec ID {monster_id} non trouvé")

        # Récupérer toutes les images
        db_images = self.image_repo.get_images_by_monster_id(int(monster.id))  # type: ignore
        images = [MonsterImageResponse.model_validate(img) for img in db_images]

        # Identifier l'image par défaut
        default_image = next((img for img in images if img.is_default), None)

        return MonsterImageListResponse(
            monster_id=monster_id,
            monster_name=monster.monster_data.get("nom", "Unknown"),
            images=images,
            default_image=default_image,
        )

    def set_default_image(self, monster_id: int, image_id: int) -> MonsterImageResponse:
        """
        Définit une image comme image par défaut pour un monstre.

        Args:
            monster_id: ID de base de données du monstre
            image_id: ID de l'image à définir comme défaut

        Returns:
            MonsterImageResponse: L'image mise à jour

        Raises:
            ValueError: Si le monstre ou l'image n'existe pas
        """
        # Récupérer le monstre
        monster = self.monster_repo.get_by_id(monster_id)
        if not monster:
            raise ValueError(f"Monstre avec ID {monster_id} non trouvé")

        # Définir l'image comme défaut
        db_image = self.image_repo.set_default_image(
            image_id=image_id,
            monster_db_id=int(monster.id),  # type: ignore
        )

        # Mettre à jour les champs image_url et description_visuelle via le service de modification
        try:
            self.monster_mod_service.update_image_and_description(
                monster_db_id=int(monster.id),  # type: ignore
                image_url=db_image.image_url,  # type: ignore
                description_visuelle=db_image.prompt,  # type: ignore
            )
            logger.info(
                f"Champs image_url et description_visuelle mis à jour pour le monstre {monster_id}"
            )
        except Exception as e:
            logger.error(
                f"Erreur lors de la mise à jour de image_url et description_visuelle: {e}"
            )
            raise
        logger.info("Données du monstre mises à jour avec la nouvelle image par défaut")

        logger.info(
            f"Image {image_id} définie comme défaut pour le monstre {monster_id}"
        )

        return MonsterImageResponse.model_validate(db_image)
