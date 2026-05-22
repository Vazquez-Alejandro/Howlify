import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("howlify", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Argentina/Buenos_Aires",
    enable_utc=True,
    task_soft_time_limit=180,
    task_time_limit=240,
    worker_max_tasks_per_child=10,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    beat_schedule={
        "vigilar-ofertas-every-minute": {
            "task": "howlify.tasks.vigilar_ofertas_task",
            "schedule": 60.0,
            "options": {"expires": 55},
        },
    },
)

import howlify.tasks  # noqa
