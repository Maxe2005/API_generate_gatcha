from pydantic import BaseModel, Field
from typing import Optional

class MonsterStats(BaseModel):
    attack: int
    defense: int
    hp: int
    speed: int

class MonsterBase(BaseModel):
    name: str = Field(..., description="The name of the monster")
    element: str = Field(..., description="Fire, Water, Earth, Air, etc.")
    rarity: str = Field(..., description="Common, Rare, Legendary")
    lore: str = Field(..., description="A short backstory for the monster")
    stats: MonsterStats

class MonsterCreateRequest(BaseModel):
    """Payload to trigger generation"""
    theme: str = Field(..., description="Theme or keyword for generation")
    rarity: Optional[str] = Field("Common", description="Desired rarity")

class MonsterResponse(MonsterBase):
    """Complete response with generated assets"""
    image_url: str = Field(..., description="URL to the generated image")
    generation_id: str
