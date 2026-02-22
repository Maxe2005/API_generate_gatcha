from app.celery_worker import celery_app
from app.services.generation_tasks import generate_monsters as real_generate_monsters


@celery_app.task(name="app.services.generation_tasks.generate_monsters")
def generate_monsters(batch_id: str, monster_count: int, prompt: str | None = None):
    return real_generate_monsters(batch_id, monster_count, prompt)
