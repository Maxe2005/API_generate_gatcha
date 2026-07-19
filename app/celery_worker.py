import nest_asyncio
from celery import Celery

from app.core.config import get_settings

nest_asyncio.apply()

settings = get_settings()
redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"

celery_app = Celery("gatcha", broker=redis_url, backend=redis_url)

# Pour auto-discover les tâches
celery_app.autodiscover_tasks(["app.services"])
