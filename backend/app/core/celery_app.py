"""Celery application and task queue configuration"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

broker_url = settings.redis_url
backend_url = settings.redis_url
if broker_url.startswith("sqla+"):
    backend_url = broker_url.replace("sqla+", "db+")

celery_app = Celery(
    "vendorsentry",
    broker=broker_url,
    backend=backend_url,
    include=[
        "app.services.monitoring.cert_watcher",
        "app.services.monitoring.breach_watcher",
        "app.services.monitoring.contract_watcher",
        "app.services.monitoring.assessment_watcher",
        "app.services.enrichment.public_records",
        "app.services.integrations.status_api",
        "app.services.extraction.tasks",
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
    "public-records-enrichment": {
        "task": "app.services.enrichment.public_records.check_public_records",
        "schedule": crontab(hour=7, minute=0),
    },
    "status-api-check": {
        "task": "app.services.integrations.status_api.check_live_cert_status",
        "schedule": crontab(hour=7, minute=15),
    },
}
