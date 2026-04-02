from celery import shared_task
from django.conf import settings
from django.utils import timezone

from services.factory import get_embedder
from services.ingestion import ingest_document

from .models import IngestionJob, IngestionStatus


@shared_task(bind=True)
def run_ingestion_job(self, job_id: str) -> dict[str, object]:
    """
    Execute a queued ingestion job and persist lifecycle state.
    """
    try:
        job = IngestionJob.objects.select_related("document").get(job_id=job_id)
    except IngestionJob.DoesNotExist:
        return {"job_id": job_id, "status": "missing"}

    if job.status == IngestionStatus.SUCCEEDED:
        return {"job_id": str(job.job_id), "status": str(job.status), "chunks_created": 0}

    job.status = IngestionStatus.RUNNING
    job.started_at = timezone.now()
    job.retries = int(getattr(self.request, "retries", 0))
    job.error_message = ""
    job.save(update_fields=["status", "started_at", "retries", "error_message"])

    try:
        chunks = ingest_document(job.document_id)
    except Exception as exc:
        max_retries = int(getattr(settings, "INGESTION_TASK_MAX_RETRIES", 3))
        retry_delay = int(getattr(settings, "INGESTION_TASK_RETRY_DELAY_SECONDS", 30))
        retries = int(getattr(self.request, "retries", 0))
        if retries < max_retries:
            job.status = IngestionStatus.QUEUED
            job.retries = retries + 1
            job.error_message = str(exc)
            job.save(update_fields=["status", "retries", "error_message"])
            raise self.retry(exc=exc, max_retries=max_retries, countdown=retry_delay)

        job.status = IngestionStatus.FAILED
        job.retries = retries
        job.error_message = str(exc)
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "retries", "error_message", "finished_at"])
        return {
            "job_id": str(job.job_id),
            "status": str(job.status),
            "chunks_created": 0,
            "error": str(exc),
        }

    job.status = IngestionStatus.SUCCEEDED
    job.finished_at = timezone.now()
    job.error_message = ""
    job.save(update_fields=["status", "finished_at", "error_message"])

    return {
        "job_id": str(job.job_id),
        "status": str(job.status),
        "chunks_created": len(chunks),
    }


@shared_task
def warm_ingestion_worker() -> dict[str, object]:
    """
    Load embedding model in worker process to reduce first-job latency.
    """
    embedder = get_embedder()
    vector = embedder.embed("warmup")
    return {"dimensions": len(vector)}
