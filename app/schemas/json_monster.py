# ========== Schémas pour les données JSON (monstres non validés) ==========

from tkinter import Image
from typing import List
from pydantic import BaseModel, Field

from app.core.constants import ElementEnum, RankEnum, StatEnum


class SkillRatio(BaseModel):
    stat: str = Field(..., description="|".join(StatEnum._member_names_))
    percent: float


class Skill(BaseModel):
    """Skill au format JSON (pour monstres non structurés)"""

    name: str
    description: str
    damage: int
    ratio: SkillRatio
    cooldown: int
    lvlMax: int
    rank: str = Field(..., description="|".join(RankEnum._member_names_))


class MonsterStats(BaseModel):
    hp: int
    atk: int
    def_: int = Field(..., alias="def")  # 'def' is a reserved keyword in Python
    vit: int


class MonsterBase(BaseModel):
    """Monstre de base au format JSON"""

    nom: str = Field(..., description="le nom du monstre")
    element: str = Field(..., description="|".join(ElementEnum._member_names_))
    rang: str = Field(..., description="|".join(RankEnum._member_names_))
    stats: MonsterStats
    description_carte: str = Field(
        ...,
        description="Description du monstre pour la carte (visible au joueur). Moins de 200 caractères.",
    )
    description_visuelle: str = Field(
        ..., description="Description visuelle détaillée."
    )
    skills: List[Skill]
    ImageUrl: str = Field(..., description="URL de l'image du monstre")
