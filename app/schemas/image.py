"""
Module: image schemas

Description:
Schémas Pydantic pour la gestion des images de monstres
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.core.constants import ImageProviderEnum


class MonsterImageBase(BaseModel):
    """Schéma de base pour une image de monstre"""

    image_name: str = Field(..., description="Nom de l'image (sans extension)")
    prompt: str = Field(..., description="Prompt utilisé pour la génération")
    is_default: bool = Field(default=False, description="Image par défaut du monstre")


class MonsterImageCreate(BaseModel):
    """Schéma pour créer une nouvelle image pour un monstre"""

    monster_id: str = Field(..., description="UUID du monstre")
    image_name: str = Field(..., description="Nom de l'image à créer")
    custom_prompt: str = Field(
        ...,
        description="Prompt personnalisé (sera injecté dans IMAGE_GENERATION)",
    )
    provider: ImageProviderEnum = Field(
        default=ImageProviderEnum.FAL,
        description="Provider de génération d'images à utiliser (fal.ai par défaut, Gemini en alternative)",
    )
    model: Optional[str] = Field(
        default=None,
        description="Modèle à utiliser pour la génération d'images (défaut du provider si non fourni)",
        examples=["fal-ai/flux/dev", "gemini-3-pro-image-preview"],
    )


class MonsterImageResponse(MonsterImageBase):
    """Schéma de réponse pour une image de monstre"""

    id: int = Field(..., description="ID unique de l'image")
    image_url: str = Field(..., description="URL complète de l'image sur MinIO")
    created_at: datetime = Field(..., description="Date de création")

    model_config = ConfigDict(from_attributes=True)


class MonsterImageListResponse(BaseModel):
    """Schéma de réponse pour la liste des images d'un monstre"""

    images: list[MonsterImageResponse] = Field(default_factory=list, description="Liste des images")
    default_image: Optional[MonsterImageResponse] = Field(None, description="Image par défaut")


class SetDefaultImageRequest(BaseModel):
    """Schéma pour définir l'image par défaut"""

    image_id: int = Field(..., description="ID de l'image à définir comme défaut")


class RenameImageRequest(BaseModel):
    """Schéma pour renommer une image"""

    new_name: str = Field(..., description="Nouveau nom de l'image")


class SignedUrlRequestItem(BaseModel):
    """Item d'entrée: identifiant interne et URL low-res publique"""

    id: int = Field(..., description="ID interne de l'image")
    url: str = Field(..., description="URL low-res publique (entrée)")


class SignedUrlResponseItem(BaseModel):
    """Item de réponse pour les URLs présignées"""

    id: int = Field(..., description="ID interne de l'image")
    input_url: str = Field(..., description="URL low-res fournie en entrée")
    signed_url: Optional[str] = Field(None, description="URL présignée pour accéder au high-res")
    expires_in: int = Field(0, description="Durée de validité en secondes")
    error: Optional[str] = Field(None, description="Message d'erreur si non générée")
