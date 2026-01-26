from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.schemas.monster import (
    MonsterCreateRequest,
    MonsterResponse,
    BatchMonsterRequest,
)
from app.services.gatcha_service import GatchaService

router = APIRouter()


# Dependency Injection for the service
async def get_gatcha_service():
    return GatchaService()


@router.post("/generate", response_model=MonsterResponse)
async def generate_monster_card(
    request: MonsterCreateRequest, service: GatchaService = Depends(get_gatcha_service)
):
    """
    Generate a full monster card with stats and image.
    """
    try:
        monster = await service.create_monster(request.prompt)
        return monster
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-batch", response_model=List[MonsterResponse])
async def generate_monster_batch(
    request: BatchMonsterRequest, service: GatchaService = Depends(get_gatcha_service)
):
    """
    Generate multiple monsters with balanced stats and concepts.
    """
    try:
        monsters = await service.create_batch_monsters(request.n, request.prompt)
        return monsters
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
