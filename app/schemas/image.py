"""
Module: image schemas

Description:
Schémas Pydantic pour la gestion des images de monstres
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class MonsterImageBase(BaseModel):
    """Schéma de base pour une image de monstre"""

    image_name: str = Field(..., description="Nom de l'image (sans extension)")
    prompt: str = Field(..., description="Prompt utilisé pour la génération")
    is_default: bool = Field(default=False, description="Image par défaut du monstre")


class MonsterImageCreate(BaseModel):
    """Schéma pour créer une nouvelle image pour un monstre"""

    monster_id: int = Field(..., description="ID du monstre")
    image_name: str = Field(..., description="Nom de l'image à créer")
    custom_prompt: str = Field(
        ...,
        description="Prompt personnalisé (sera injecté dans IMAGE_GENERATION)",
    )


class MonsterImageResponse(MonsterImageBase):
    """Schéma de réponse pour une image de monstre"""

    id: int = Field(..., description="ID unique de l'image")
    monster_id: int = Field(..., description="ID du monstre associé")
    image_url: str = Field(..., description="URL complète de l'image sur MinIO")
    created_at: datetime = Field(..., description="Date de création")

    model_config = ConfigDict(from_attributes=True)


class MonsterImageListResponse(BaseModel):
    """Schéma de réponse pour la liste des images d'un monstre"""

    monster_id: int = Field(..., description="ID du monstre")
    monster_name: str = Field(..., description="Nom du monstre")
    images: list[MonsterImageResponse] = Field(
        default_factory=list, description="Liste des images"
    )
    default_image: Optional[MonsterImageResponse] = Field(
        None, description="Image par défaut"
    )


class SetDefaultImageRequest(BaseModel):
    """Schéma pour définir l'image par défaut"""

    image_id: int = Field(..., description="ID de l'image à définir comme défaut")
