"""Celery application and task queue configuration"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "vendorsentry",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.services.monitoring.cert_watcher",
        "app.services.monitoring.breach_watcher",
        "app.services.monitoring.contract_watcher",
        "app.services.monitoring.assessment_watcher",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Celery Beat schedule for monitoring sweeps (simulated daily)
celery_app.conf.beat_schedule = {
    "cert-expiry-sweep": {
        "task": "app.services.monitoring.cert_watcher.check_cert_expiry",
        "schedule": crontab(hour=6, minute=0),  # Daily at 6 AM UTC
    },
    "contract-expiry-sweep": {
        "task": "app.services.monitoring.contract_watcher.check_contract_expiry",
        "schedule": crontab(hour=6, minute=15),
    },
    "assessment-overdue-sweep": {
        "task": "app.services.monitoring.assessment_watcher.check_assessment_overdue",
        "schedule": crontab(hour=6, minute=30),
    },
    "breach-db-poll": {
        "task": "app.services.monitoring.breach_watcher.poll_breach_db",
        "schedule": crontab(hour="*/6", minute=0),  # Every 6 hours
    },
}
