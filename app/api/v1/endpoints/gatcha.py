from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.orm import Session
from app.schemas.req_res_api import MonsterCreateRequest, BatchMonsterRequest
from app.services.gatcha_service import GatchaService
from app.models.base import get_db
from app.utils.ws_relay import relay_batch_messages

import uuid
from app.services.tasks import generate_monsters
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency Injection for the service
async def get_gatcha_service(db: Session = Depends(get_db)):
    return GatchaService(db)


@router.post("/generate", response_model=dict)
def generate_monster_card(request: MonsterCreateRequest):
    """
    Lance la génération d'un monstre en tâche de fond (Celery).
    Retourne un batch_id pour le suivi via WebSocket.
    """
    batch_id = str(uuid.uuid4())
    generate_monsters.delay(batch_id, 1, request.prompt) # pyright: ignore[reportFunctionMemberAccess]
    return {"batch_id": batch_id}


@router.post("/generate-batch", response_model=dict)
def generate_monster_batch(request: BatchMonsterRequest):
    """
    Lance la génération batch en tâche de fond (Celery).
    Retourne un batch_id pour le suivi via WebSocket.
    """
    batch_id = str(uuid.uuid4())
    generate_monsters.delay(batch_id, request.n, request.prompt) # pyright: ignore[reportFunctionMemberAccess]
    return {"batch_id": batch_id}


@router.websocket("/ws/{batch_id}")
async def websocket_batch(websocket: WebSocket, batch_id: str):
    await relay_batch_messages(websocket, batch_id)
