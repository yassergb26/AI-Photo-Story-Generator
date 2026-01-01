"""
Celery Application Configuration
Handles async task processing for long-running operations
"""
from celery import Celery
from app.config import settings

# Create Celery app
celery_app = Celery(
    "photo_story_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.tasks']  # Import tasks module
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,  # One task at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    result_expires=3600,  # Results expire after 1 hour
)

# Task routing - Commented out to use default 'celery' queue
# celery_app.conf.task_routes = {
#     'app.tasks.process_image_batch': {'queue': 'image_processing'},
#     'app.tasks.classify_image_task': {'queue': 'classification'},
#     'app.tasks.detect_emotions_task': {'queue': 'emotion_detection'},
#     'app.tasks.generate_story_arcs_task': {'queue': 'story_generation'},
# }
