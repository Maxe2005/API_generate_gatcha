import nest_asyncio
from celery import Celery

nest_asyncio.apply()

celery_app = Celery(
    "gatcha", broker="redis://redis:6379/0", backend="redis://redis:6379/0"
)

# Pour auto-discover les tâches
celery_app.autodiscover_tasks(["app.services"])
