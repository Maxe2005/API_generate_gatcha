from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.schemas.req_res_api import MonsterCreateRequest, BatchMonsterRequest
from app.services.gatcha_service import GatchaService
from app.models.base import get_db

import uuid
from app.services.tasks import generate_monsters
import redis.asyncio as aioredis
import asyncio
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
    settings = get_settings()
    await websocket.accept()
    logger.info(f"WebSocket connecté pour batch_id={batch_id}")
    redis = await aioredis.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0", decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"batch:{batch_id}")
    try:
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if message and message["type"] == "message":
                msg = message["data"]
                logger.info(f"Envoi WebSocket batch_id={batch_id} : {msg[:100]}")
                await websocket.send_text(msg)
                if msg == "Génération terminée":
                    break
            await asyncio.sleep(0.1)
    finally:
        await pubsub.unsubscribe(f"batch:{batch_id}")
        await pubsub.close()
        await redis.close()
    await websocket.close()
    logger.info(f"WebSocket fermé pour batch_id={batch_id}")
