from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "bmc_master",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.monitoring", "app.tasks.discovery", "app.tasks.alerts", "app.tasks.sel", "app.tasks.bulk", "app.tasks.scheduler"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Beat schedule for periodic tasks
    beat_schedule={
        "collect-sensors": {
            "task": "app.tasks.monitoring.collect_all_servers_sensors",
            "schedule": 30.0,  # every 30 seconds
        },
        "collect-sel": {
            "task": "app.tasks.sel.collect_all_sel_logs",
            "schedule": 300.0,  # every 5 minutes
        },
        "evaluate-alerts": {
            "task": "app.tasks.alerts.evaluate_alert_rules",
            "schedule": 60.0,  # every minute
        },
        "check-scheduled-tasks": {
            "task": "app.tasks.scheduler.check_and_run_due_tasks",
            "schedule": 60.0,  # every minute
        },
        "cleanup-task-history": {
            "task": "app.tasks.scheduler.cleanup_old_execution_history",
            "schedule": 86400.0,  # every 24 hours
            "kwargs": {"days": 30},
        },
    },
)
