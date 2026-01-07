from celery import Task
from app.celery_client import celery_app


@celery_app.task(bind=True, name='app.tasks.process_call_task')
def process_call_task(self, job_id: int):
    """
    Process call recording task
    This is a stub that will be properly implemented in the worker
    """
    # The actual implementation is in the worker app
    pass








