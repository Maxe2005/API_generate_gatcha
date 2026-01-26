from pydantic import BaseModel, Field
from typing import List


class SkillRatio(BaseModel):
    stat: str = Field(..., description="ATK|DEF|HP|VIT")
    percent: float


class Skill(BaseModel):
    name: str
    description: str
    damage: float
    ratio: SkillRatio
    cooldown: float
    lvlMax: float
    rank: str = Field(..., description="COMMON|RARE|EPIC|LEGENDARY")


class MonsterStats(BaseModel):
    hp: float
    atk: float
    def_: float = Field(..., alias="def")  # 'def' is a reserved keyword in Python
    vit: float


class MonsterBase(BaseModel):
    nom: str = Field(..., description="TEMPLATE - Remplacer par le nom du monstre")
    element: str = Field(..., description="FIRE|WATER|WIND|EARTH")
    rang: str = Field(..., description="COMMON|RARE|EPIC|LEGENDARY")
    stats: MonsterStats
    description_carte: str = Field(
        ...,
        description="Description du monstre pour la carte (visible au joueur). Moins de 200 caractères.",
    )
    description_visuelle: str = Field(
        ..., description="Description visuelle détaillée."
    )
    skills: List[Skill]


class MonsterCreateRequest(BaseModel):
    """Payload to trigger generation"""

    prompt: str = Field(
        ...,
        description="Prompt to guide monster generation",
        examples=["Cyberpunk Dragon"],
    )


class BatchMonsterRequest(BaseModel):
    """Payload to trigger batch generation"""

    n: int = Field(..., description="Number of monsters to generate", ge=2, le=15)
    prompt: str = Field(
        ...,
        description="Prompt to guide the batch generation",
        examples=["A team of elemental knights"],
    )


class MonsterResponse(MonsterBase):
    """Complete response with generated assets"""

    image_path: str = Field(..., description="Local path to the generated image")
    json_path: str = Field(..., description="Local path to the generated json")
