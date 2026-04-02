import uuid

import pytest
from rest_framework.test import APIClient

from apps.documents.models import Document, IngestionJob, IngestionStatus
from tests.conftest import requires_postgres


@requires_postgres
@pytest.mark.django_db
def test_ingest_endpoint_enqueues_job_and_returns_202(sample_document):
    client = APIClient()

    response = client.post(f"/api/documents/{sample_document.id}/ingest/", data={}, format="json")

    assert response.status_code == 202
    assert "job_id" in response.data

    job = IngestionJob.objects.get(job_id=response.data["job_id"])
    assert job.document_id == sample_document.id
    assert job.status in {
        IngestionStatus.QUEUED,
        IngestionStatus.RUNNING,
        IngestionStatus.SUCCEEDED,
    }


@requires_postgres
@pytest.mark.django_db
def test_ingest_endpoint_reuses_active_job():
    client = APIClient()
    document = Document.objects.create(title="Doc", content="Hello world")
    existing_job = IngestionJob.objects.create(document=document, status=IngestionStatus.QUEUED)

    response = client.post(f"/api/documents/{document.id}/ingest/", data={}, format="json")

    assert response.status_code == 202
    assert str(existing_job.job_id) == str(response.data["job_id"])
    assert IngestionJob.objects.filter(document=document).count() == 1


@requires_postgres
@pytest.mark.django_db
def test_ingest_endpoint_returns_404_for_missing_document():
    client = APIClient()

    response = client.post("/api/documents/999999/ingest/", data={}, format="json")

    assert response.status_code == 404


@requires_postgres
@pytest.mark.django_db
def test_ingestion_job_status_endpoint_returns_job(sample_document):
    client = APIClient()
    job = IngestionJob.objects.create(document=sample_document, status=IngestionStatus.RUNNING)

    response = client.get(f"/api/documents/ingest-jobs/{job.job_id}/")

    assert response.status_code == 200
    assert response.data["job_id"] == str(job.job_id)
    assert response.data["status"] == IngestionStatus.RUNNING


@requires_postgres
@pytest.mark.django_db
def test_ingestion_job_status_endpoint_404_for_unknown_job():
    client = APIClient()

    response = client.get(f"/api/documents/ingest-jobs/{uuid.uuid4()}/")

    assert response.status_code == 404


def test_ingestion_warm_endpoint_returns_202():
    client = APIClient()

    response = client.post("/api/documents/ingestion/warm/", data={}, format="json")

    assert response.status_code == 202
    assert response.data["status"] == "queued"
