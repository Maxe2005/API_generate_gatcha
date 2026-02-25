import json
import redis.asyncio as aioredis
from app.core.config import get_settings
import logging
import asyncio

logger = logging.getLogger(__name__)


async def send_completion_message(batch_id: str):
    message = json.dumps({"success": "Génération terminée"})
    await send(batch_id, message)


async def send_monster_update(batch_id: str, monster_data: dict):
    monster = json.dumps(monster_data)
    message = json.dumps({"monster": monster})
    await send(batch_id, message)


async def send_info_message(batch_id: str, info: str):
    message = json.dumps({"info": info})
    await send(batch_id, message)


async def send_error_message(batch_id: str, error: str):
    message = json.dumps({"error": error})
    await send(batch_id, message)


async def send(batch_id: str, message: str):
    settings = get_settings()
    redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
    redis_client = await aioredis.from_url(redis_url, decode_responses=True)
    logger.info(
        f"[send_info_message] Publishing to {redis_url} on channel batch:{batch_id} : {message}"
    )
    try:
        result = await redis_client.publish(f"batch:{batch_id}", message)
        logger.info(f"[send_info_message] Publish result: {result}")
    except Exception as e:
        logger.error(f"[send_info_message] Error publishing: {e}")
    await redis_client.close()


# Utilitaire pour exécuter une coroutine dans n'importe quel contexte (sync/async)
def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)
