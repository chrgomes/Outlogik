"""The Celery worker and scheduler (beat).

Run in staging and production as its own process, from the API's image:

    celery -A app.worker worker --beat --concurrency 2 --loglevel INFO

--beat runs the scheduler inside the worker: run exactly one such process. In development and
tests, jobs run inline instead (JOBS_MODE=inline), so no worker is needed.
"""

import ssl
import tempfile
import uuid
from pathlib import Path

from celery import Celery
from celery.schedules import crontab

import app.jobs.handlers  # noqa: F401 - registers the job kinds
from app.core.config import get_settings
from app.jobs.service import enqueue, run

settings = get_settings()
celery = Celery("outlogik", broker=settings.redis_url)
celery.conf.update(
    task_default_queue=settings.jobs_queue,
    task_acks_late=True,              # a job interrupted by a restart is delivered again…
    task_reject_on_worker_lost=True,  # …and claiming in run() keeps it from running twice
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    timezone="America/Toronto",
    # The schedule's state file goes where the (non-root) container can always write.
    beat_schedule_filename=str(Path(tempfile.gettempdir()) / "outlogik-celerybeat-schedule"),
    beat_schedule={
        "recover-jobs": {"task": "app.worker.scheduled", "schedule": 300.0,
                         "args": ["jobs.recover"]},
        "nightly-cleanup": {"task": "app.worker.scheduled",
                            "schedule": crontab(hour=3, minute=17),
                            "args": ["maintenance.cleanup"]},
    },
)
if settings.redis_url.startswith("rediss://"):
    # DigitalOcean's managed Valkey only accepts TLS.
    celery.conf.broker_use_ssl = {"ssl_cert_reqs": ssl.CERT_REQUIRED}


@celery.task(name="app.worker.run_job")
def run_job(job_id: str) -> str | None:
    return run(uuid.UUID(job_id))


@celery.task(name="app.worker.scheduled")
def scheduled(kind: str) -> None:
    """Scheduled work goes through the jobs table too, so it's recorded and never doubled."""
    enqueue(kind, dedupe_key=f"schedule:{kind}")
