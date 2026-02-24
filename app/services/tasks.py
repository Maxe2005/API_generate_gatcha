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

    try:
        if monster_count == 1:
            # Génération simple
            result = asyncio.run(service.create_monster(prompt or "", batch_id))
            if result is None:
                return
        else:
            # Génération batch
            result = asyncio.run(
                service.create_batch_monsters(monster_count, prompt or "", batch_id)
            )
            # Si la génération a échoué (ex: quota Gemini épuisé), on arrête proprement
            if result == []:
                return
        asyncio.run(send_completion_message(batch_id))
    except Exception as e:
        import traceback
        from app.utils.send_messages_utils import send_info_message

        tb = traceback.format_exc()
        print(f"[CeleryTaskError] {e}\n{tb}")
        # Envoi d'un message d'erreur au front
        asyncio.run(
            send_info_message(batch_id, f"Erreur critique lors de la génération : {e}")
        )
    finally:
        db.close()
