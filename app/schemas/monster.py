from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from enum import Enum
from datetime import datetime


class TransitionAction(str, Enum):
    """Actions possibles pour les transitions"""

    APPROVE = "approve"
    REJECT = "reject"
    CORRECT = "correct"
    TRANSMIT = "transmit"


# ========== Schémas pour les données JSON (monstres non validés) ==========


class SkillRatio(BaseModel):
    stat: str = Field(..., description="ATK|DEF|HP|VIT")
    percent: float


class Skill(BaseModel):
    """Skill au format JSON (pour monstres non structurés)"""

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
    """Monstre de base au format JSON"""

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


# ========== Schémas pour les données structurées (monstres validés) ==========


class SkillStructured(BaseModel):
    """Skill stockée en base de données (table skills)"""

    id: Optional[int] = None
    name: str
    description: str
    damage: float
    cooldown: float
    lvl_max: float
    rank: str = Field(..., description="COMMON|RARE|EPIC|LEGENDARY")
    ratio_stat: str = Field(..., description="ATK|DEF|HP|VIT")
    ratio_percent: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SkillCreate(BaseModel):
    """Données nécessaires pour créer une skill"""

    name: str
    description: str
    damage: float
    cooldown: float
    lvl_max: float
    rank: str = Field(..., description="COMMON|RARE|EPIC|LEGENDARY")
    ratio_stat: str = Field(..., description="ATK|DEF|HP|VIT")
    ratio_percent: float


class SkillUpdate(BaseModel):
    """Données modifiables d'une skill"""

    name: Optional[str] = None
    description: Optional[str] = None
    damage: Optional[float] = None
    cooldown: Optional[float] = None
    lvl_max: Optional[float] = None
    rank: Optional[str] = None
    ratio_stat: Optional[str] = None
    ratio_percent: Optional[float] = None


class MonsterStructured(BaseModel):
    """Monstre structuré stocké en base de données (table monsters)"""

    id: Optional[int] = None
    monster_state_id: int
    nom: str
    element: str = Field(..., description="FIRE|WATER|WIND|EARTH")
    rang: str = Field(..., description="COMMON|RARE|EPIC|LEGENDARY")
    hp: float
    atk: float
    def_: float
    vit: float
    description_carte: str
    description_visuelle: str
    skills: List[SkillStructured] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MonsterCreate(BaseModel):
    """Données nécessaires pour créer un monstre structuré (depuis JSON)"""

    nom: str
    element: str = Field(..., description="FIRE|WATER|WIND|EARTH")
    rang: str = Field(..., description="COMMON|RARE|EPIC|LEGENDARY")
    hp: float
    atk: float
    def_: float
    vit: float
    description_carte: str
    description_visuelle: str
    skills: List[SkillCreate]


class MonsterUpdate(BaseModel):
    """Données modifiables d'un monstre structuré"""

    nom: Optional[str] = None
    element: Optional[str] = None
    rang: Optional[str] = None
    hp: Optional[float] = None
    atk: Optional[float] = None
    def_: Optional[float] = None
    vit: Optional[float] = None
    description_carte: Optional[str] = None
    description_visuelle: Optional[str] = None


# ========== Schémas de requête/réponse API ==========


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


class ValidationErrorDetail(BaseModel):
    """Detail of a validation error"""

    field: str
    error_type: str
    message: str


class MonsterResponse(MonsterBase):
    """Complete response with generated assets"""

    image_path: str = Field(..., description="Local path to the generated image")
    json_path: str = Field(..., description="Local path to the generated json")

    model_config = ConfigDict(extra="allow")


class MonsterWithValidationStatus(BaseModel):
    """Monster response with validation status"""

    monster: MonsterResponse
    is_valid: bool = Field(
        ..., description="Whether the monster passed all validations"
    )
    validation_errors: Optional[List[ValidationErrorDetail]] = Field(
        default=None, description="List of validation errors if is_valid is False"
    )
