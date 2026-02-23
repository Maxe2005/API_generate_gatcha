from app.celery_worker import celery_app
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.gatcha_service import GatchaService
from app.core.config import get_settings
from app.utils.send_messages_utils import send_completion_message

@celery_app.task(name="app.services.generation_tasks.generate_monsters")
def generate_monsters(batch_id: str, monster_count: int, prompt: str | None = None):
    """
    Génère un ou plusieurs monstres en tâche de fond, publie sur Redis à chaque monstre.
    """

    # Connexion DB et settings
    settings = get_settings()

    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    service = GatchaService(db)

    if monster_count == 1:
        # Génération simple
        asyncio.run(service.create_monster(prompt or "", batch_id))
    else:
        # Génération batch
        asyncio.run(
            service.create_batch_monsters(monster_count, prompt or "", batch_id)
        )
    send_completion_message(batch_id)

    # Message de fin
    db.close()
