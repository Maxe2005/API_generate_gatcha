from fastapi import APIRouter, HTTPException, Depends
from app.schemas.monster import MonsterCreateRequest, MonsterResponse
from app.services.gatcha_service import GatchaService

router = APIRouter()

# Dependency Injection for the service
async def get_gatcha_service():
    return GatchaService()

@router.post("/generate", response_model=MonsterResponse)
async def generate_monster_card(
    request: MonsterCreateRequest,
    service: GatchaService = Depends(get_gatcha_service)
):
    """
    Generate a full monster card with stats and image.
    """
    try:
        if not request.rarity:
            raise HTTPException(status_code=400, detail="Rarity is required")
        monster = await service.create_monster(request.theme, request.rarity)
        return monster
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
