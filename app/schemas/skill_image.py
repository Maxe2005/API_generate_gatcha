"""
Module: skill_image schemas

Description:
Schémas Pydantic pour la gestion des cartes de compétence (images générées
par IA illustrant une compétence en conservant l'identité visuelle du
monstre). Miroir de app/schemas/image.py.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

from app.core.constants import ImageProviderEnum


class SkillImageCreate(BaseModel):
    """Schéma pour générer une nouvelle carte de compétence"""

    skill_id: int = Field(..., description="ID de la compétence")
    custom_prompt: Optional[str] = Field(
        default=None,
        description="Prompt personnalisé (sinon généré depuis le nom/la description de la compétence)",
    )
    provider: ImageProviderEnum = Field(
        default=ImageProviderEnum.FAL,
        description="Provider de génération d'images à utiliser (fal.ai par défaut, Gemini en alternative)",
    )
    model: Optional[str] = Field(
        default=None,
        description="Modèle à utiliser pour la génération d'images (défaut du provider si non fourni)",
    )


class SkillImageResponse(BaseModel):
    """Schéma de réponse pour une carte de compétence"""

    id: int = Field(..., description="ID unique de la carte")
    skill_id: int = Field(..., description="ID de la compétence")
    source_monster_image_id: int = Field(
        ..., description="ID de l'image de monstre utilisée comme référence"
    )
    image_url: str = Field(..., description="URL complète de l'image sur MinIO")
    prompt: str = Field(..., description="Prompt utilisé pour la génération")
    provider: str = Field(..., description="Provider IA utilisé pour la génération")
    model: Optional[str] = Field(None, description="Modèle utilisé pour la génération")
    is_default: bool = Field(default=False, description="Carte par défaut du groupe")
    created_at: datetime = Field(..., description="Date de création")

    model_config = ConfigDict(from_attributes=True)


class SkillImageListResponse(BaseModel):
    """Schéma de réponse pour la liste des cartes d'une compétence (un groupe donné)"""

    images: list[SkillImageResponse] = Field(default_factory=list, description="Liste des cartes")
    default_image: Optional[SkillImageResponse] = Field(None, description="Carte par défaut")
    source_monster_image_id: Optional[int] = Field(
        None, description="Image de monstre source du groupe renvoyé"
    )


class SetDefaultSkillImageRequest(BaseModel):
    """Schéma pour définir la carte par défaut d'un groupe"""

    image_id: int = Field(..., description="ID de la carte à définir comme défaut")
