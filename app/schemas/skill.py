from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import RankEnum, StatEnum


class SkillStructured(BaseModel):
    """Skill stockée en base de données (table skills)"""

    id: Optional[int] = None
    name: str
    description: str
    damage: int
    cooldown: int
    lvl_max: int
    rank: str = Field(..., description="|".join(RankEnum._member_names_))
    ratio_stat: str = Field(..., description="|".join(StatEnum._member_names_))
    ratio_percent: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SkillCreate(BaseModel):
    """Données nécessaires pour créer une skill"""

    name: str
    description: str
    damage: int
    cooldown: int
    lvl_max: int
    rank: str = Field(..., description="|".join(RankEnum._member_names_))
    ratio_stat: str = Field(..., description="|".join(StatEnum._member_names_))
    ratio_percent: float


class SkillUpdate(BaseModel):
    """Données modifiables d'une skill"""

    name: Optional[str] = None
    description: Optional[str] = None
    damage: Optional[int] = None
    cooldown: Optional[int] = None
    lvl_max: Optional[int] = None
    rank: Optional[str] = None
    ratio_stat: Optional[str] = None
    ratio_percent: Optional[float] = None

