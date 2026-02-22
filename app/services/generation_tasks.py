from app.celery_worker import celery_app

import asyncio
import json
import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.gatcha_service import GatchaService
from app.core.config import get_settings


@celery_app.task
def generate_monsters(batch_id: str, monster_count: int, prompt: str | None =None):
    """
    Génère un ou plusieurs monstres en tâche de fond, publie sur Redis à chaque monstre.
    """
    # Connexion Redis
    redis_client = redis.Redis(host="localhost", port=6379, db=0)

    # Connexion DB
    settings = get_settings()
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    service = GatchaService(db)

    monsters = []
    if monster_count == 1:
        # Génération simple
        monster = asyncio.run(service.create_monster(prompt or ""))
        monsters.append(monster)
        redis_client.publish(f"batch:{batch_id}", json.dumps(monster.dict()))
    else:
        # Génération batch
        batch = asyncio.run(service.create_batch_monsters(monster_count, prompt or ""))
        for monster in batch:
            redis_client.publish(f"batch:{batch_id}", json.dumps(monster.dict()))
            monsters.append(monster)

    # Message de fin
    redis_client.publish(f"batch:{batch_id}", "Génération terminée")
    db.close()
