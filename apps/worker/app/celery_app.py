from celery import Celery
from app.config import settings

celery_app = Celery(
    "kommo_analyzer_worker",
    broker=settings.redis_url,
    backend=settings.redis_url
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
)

# Import tasks
from app.tasks import process_call_task








