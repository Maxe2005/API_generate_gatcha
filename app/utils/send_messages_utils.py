import json
import redis.asyncio as aioredis
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)


async def send_completion_message(batch_id: str):
    settings = get_settings()
    redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
    redis_client = await aioredis.from_url(redis_url, decode_responses=True)
    logger.info(
        f"[send_completion_message] Publishing to {redis_url} on channel batch:{batch_id} : Génération terminée"
    )
    try:
        result = await redis_client.publish(f"batch:{batch_id}", "Génération terminée")
        logger.info(f"[send_completion_message] Publish result: {result}")
    except Exception as e:
        logger.error(f"[send_completion_message] Error publishing: {e}")
    await redis_client.close()


async def send_monster_update(batch_id: str, monster_data: dict):
    settings = get_settings()
    redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
    redis_client = await aioredis.from_url(redis_url, decode_responses=True)
    monster = json.dumps(monster_data)
    message = json.dumps({"monster": monster})
    logger.info(
        f"[send_monster_update] Publishing to {redis_url} on channel batch:{batch_id} : {message[:100]}"
    )
    try:
        result = await redis_client.publish(f"batch:{batch_id}", message)
        logger.info(f"[send_monster_update] Publish result: {result}")
    except Exception as e:
        logger.error(f"[send_monster_update] Error publishing: {e}")
    await redis_client.close()


async def send_info_message(batch_id: str, info: str):
    settings = get_settings()
    redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
    redis_client = await aioredis.from_url(redis_url, decode_responses=True)
    message = json.dumps({"info": info})
    logger.info(
        f"[send_info_message] Publishing to {redis_url} on channel batch:{batch_id} : {message}"
    )
    try:
        result = await redis_client.publish(f"batch:{batch_id}", message)
        logger.info(f"[send_info_message] Publish result: {result}")
    except Exception as e:
        logger.error(f"[send_info_message] Error publishing: {e}")
    await redis_client.close()
