from app.celery_worker import celery_app
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.gatcha_service import GatchaService
from app.services.image_service import ImageService
from app.clients.banana import BananaClient
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
            asyncio.run(service.create_monster(prompt or "", batch_id))
        else:
            # Génération batch
            asyncio.run(service.create_batch_monsters(monster_count, prompt or "", batch_id))
    except Exception as e:
        import traceback
        from app.utils.send_messages_utils import send_info_message

        tb = traceback.format_exc()
        print(f"[CeleryTaskError] {e}\n{tb}")
        # Envoi d'un message d'erreur au front
        asyncio.run(send_info_message(batch_id, f"Erreur critique lors de la génération : {e}"))
    finally:
        # Toujours publier le message terminal, sinon les WebSockets abonnés
        # au batch ne se ferment jamais (échec Gemini, quota, crash...)
        asyncio.run(send_completion_message(batch_id))
        db.close()


@celery_app.task(name="app.services.generation_tasks.generate_custom_image")
def generate_custom_image(
    batch_id: str,
    monster_id: str,
    image_name: str,
    custom_prompt: str,
    model: str = "gemini-3-pro-image-preview",
):
    """
    Génère une image personnalisée pour un monstre en tâche de fond, publie sur Redis.
    """

    # Connexion DB et settings
    settings = get_settings()

    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    banana_client = BananaClient()
    service = ImageService(db, banana_client)

    try:
        # Génération de l'image personnalisée
        asyncio.run(
            service.create_custom_image_for_monster(
                monster_id=monster_id,
                image_name=image_name,
                custom_prompt=custom_prompt,
                model=model,
            )
        )
    except Exception as e:
        import traceback
        from app.utils.send_messages_utils import send_info_message

        tb = traceback.format_exc()
        print(f"[CeleryTaskError] {e}\n{tb}")
        # Envoi d'un message d'erreur au front
        asyncio.run(
            send_info_message(batch_id, f"Erreur critique lors de la génération d'image : {e}")
        )
    finally:
        # Toujours publier le message terminal pour fermer les WebSockets abonnés
        asyncio.run(send_completion_message(batch_id))
        db.close()
