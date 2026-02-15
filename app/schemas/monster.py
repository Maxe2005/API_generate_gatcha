from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

from app.core.constants import ElementEnum, RankEnum
from app.schemas.skill import SkillCreate, SkillStructured


class MonsterStructured(BaseModel):
    """Monstre structuré stocké en base de données (table monsters)"""

    id: Optional[int] = None
    monster_uuid: Optional[str] = None  # UUID pour référence externe
    monster_state_id: int
    nom: str
    element: str = Field(..., description="|".join(ElementEnum._member_names_))
    rang: str = Field(..., description="|".join(RankEnum._member_names_))
    hp: int
    atk: int
    def_: int
    vit: int
    description_carte: str
    description_visuelle: str
    skills: List[SkillStructured] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MonsterCreate(BaseModel):
    """Données nécessaires pour créer un monstre structuré (depuis JSON)"""

    nom: str
    element: str = Field(..., description="|".join(ElementEnum._member_names_))
    rang: str = Field(..., description="|".join(RankEnum._member_names_))
    hp: int
    atk: int
    def_: int
    vit: int
    description_carte: str
    description_visuelle: str
    skills: List[SkillCreate]


class MonsterUpdate(BaseModel):
    """Données modifiables d'un monstre structuré"""

    nom: Optional[str] = None
    element: Optional[str] = None
    rang: Optional[str] = None
    hp: Optional[int] = None
    atk: Optional[int] = None
    def_: Optional[int] = None
    vit: Optional[int] = None
    description_carte: Optional[str] = None
    description_visuelle: Optional[str] = None
