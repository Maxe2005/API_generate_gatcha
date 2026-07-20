"""
Module: ws_relay

Description:
Relais des messages Redis pub/sub (canal batch:{batch_id}) vers un WebSocket.
Boucle partagée par les endpoints de suivi de génération (monstres et images).
"""

import asyncio
import logging

import redis.asyncio as aioredis
from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.utils.send_messages_utils import is_terminal_message

logger = logging.getLogger(__name__)


async def relay_batch_messages(websocket: WebSocket, batch_id: str) -> None:
    """
    Accepte la connexion WebSocket, s'abonne au canal Redis batch:{batch_id}
    et relaie chaque message jusqu'au message terminal (clé "success").

    Ferme proprement l'abonnement Redis et le WebSocket dans tous les cas
    (fin de génération, déconnexion client, erreur).
    """
    settings = get_settings()
    await websocket.accept()
    logger.info(f"WebSocket connecté pour batch_id={batch_id}")

    redis = await aioredis.from_url(
        f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
        decode_responses=True,
    )
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"batch:{batch_id}")
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                msg = message["data"]
                logger.info(f"Envoi WebSocket batch_id={batch_id} : {msg[:100]}")
                await websocket.send_text(msg)
                if is_terminal_message(msg):
                    break
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        logger.info(f"Client WebSocket déconnecté pour batch_id={batch_id}")
    finally:
        await pubsub.unsubscribe(f"batch:{batch_id}")
        await pubsub.close()
        await redis.close()
        try:
            await websocket.close()
        except RuntimeError:
            # Déjà fermé côté client
            pass
        logger.info(f"WebSocket fermé pour batch_id={batch_id}")
