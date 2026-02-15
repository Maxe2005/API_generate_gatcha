# ========== Schémas de requête/réponse API ==========


from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.json_monster import MonsterBase


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
