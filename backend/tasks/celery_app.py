from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "animateai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.script_tasks",
        "app.tasks.scene_tasks",
        "app.tasks.voice_tasks",
        "app.tasks.render_tasks",
        "app.tasks.export_tasks",
        "app.tasks.cleanup_tasks",
        "app.tasks.notification_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=600,
    task_time_limit=900,
    task_max_retries=3,
    task_default_retry_delay=60,
    result_expires=86400,
    beat_schedule={
        "cleanup-expired-files": {
            "task": "app.tasks.cleanup_tasks.cleanup_expired_files",
            "schedule": 3600.0,
        },
    },
    task_routes={
        "app.tasks.render_tasks.*": {"queue": "render"},
        "app.tasks.script_tasks.*": {"queue": "ai"},
        "app.tasks.scene_tasks.*": {"queue": "ai"},
        "app.tasks.voice_tasks.*": {"queue": "voice"},
        "app.tasks.export_tasks.*": {"queue": "export"},
    },
    task_queues={
        "default": {"exchange": "default", "routing_key": "default"},
        "render": {"exchange": "render", "routing_key": "render"},
        "ai": {"exchange": "ai", "routing_key": "ai"},
        "voice": {"exchange": "voice", "routing_key": "voice"},
        "export": {"exchange": "export", "routing_key": "export"},
    },
    task_default_queue="default",
)
