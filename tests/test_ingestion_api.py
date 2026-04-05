import uuid

import pytest
from rest_framework.test import APIClient

from apps.documents.models import Document, IngestionJob, IngestionStatus
from tests.conftest import requires_postgres


@requires_postgres
@pytest.mark.django_db
def test_ingest_endpoint_enqueues_job_and_returns_202(sample_document, sample_user, sample_project):
    client = APIClient()
    client.force_authenticate(user=sample_user)
    sample_document.project = sample_project
    sample_document.save(update_fields=["project"])

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
def test_ingest_endpoint_reuses_active_job(sample_user, sample_project):
    client = APIClient()
    client.force_authenticate(user=sample_user)
    document = Document.objects.create(title="Doc", content="Hello world", project=sample_project)
    existing_job = IngestionJob.objects.create(document=document, status=IngestionStatus.QUEUED)

    response = client.post(f"/api/documents/{document.id}/ingest/", data={}, format="json")

    assert response.status_code == 202
    assert str(existing_job.job_id) == str(response.data["job_id"])
    assert IngestionJob.objects.filter(document=document).count() == 1


@requires_postgres
@pytest.mark.django_db
def test_ingest_endpoint_returns_404_for_missing_document(sample_user):
    client = APIClient()
    client.force_authenticate(user=sample_user)

    response = client.post("/api/documents/999999/ingest/", data={}, format="json")

    assert response.status_code == 404


@requires_postgres
@pytest.mark.django_db
def test_ingestion_job_status_endpoint_returns_job(sample_document, sample_user, sample_project):
    client = APIClient()
    client.force_authenticate(user=sample_user)
    sample_document.project = sample_project
    sample_document.save(update_fields=["project"])
    job = IngestionJob.objects.create(document=sample_document, status=IngestionStatus.RUNNING)

    response = client.get(f"/api/documents/ingest-jobs/{job.job_id}/")

    assert response.status_code == 200
    assert response.data["job_id"] == str(job.job_id)
    assert response.data["status"] == IngestionStatus.RUNNING


@requires_postgres
@pytest.mark.django_db
def test_ingestion_job_status_endpoint_404_for_unknown_job(sample_user):
    client = APIClient()
    client.force_authenticate(user=sample_user)

    response = client.get(f"/api/documents/ingest-jobs/{uuid.uuid4()}/")

    assert response.status_code == 404


@requires_postgres
@pytest.mark.django_db
def test_ingestion_warm_endpoint_returns_202(sample_user):
    client = APIClient()
    client.force_authenticate(user=sample_user)

    response = client.post("/api/documents/ingestion/warm/", data={}, format="json")

    assert response.status_code == 202
    assert response.data["status"] == "queued"


@requires_postgres
@pytest.mark.django_db
def test_generate_welcome_message_returns_length_limited_message(sample_user, sample_project, monkeypatch):
    client = APIClient()
    client.force_authenticate(user=sample_user)

    Document.objects.create(
        title="Pricing Sheet",
        content="40ft container pricing, discounts, and payment terms.",
        project=sample_project,
        processed=True,
    )

    class FakeLLM:
        def complete(self, prompt: str) -> str:
            return (
                "Hello and welcome to your assistant. "
                "I can help with pricing, discounts, delivery timelines, and policy questions from your documents. "
                "Ask me anything about product options, costs, and next steps for your purchase today."
            )

    monkeypatch.setattr("apps.documents.views.get_llm_client_for_project", lambda project: FakeLLM())

    response = client.post(
        "/api/documents/welcome-message/generate/",
        data={"project_id": sample_project.id, "max_length": 160},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["message"]
    assert len(response.data["message"]) <= 160
    assert response.data["source_document_count"] == 1


@requires_postgres
@pytest.mark.django_db
def test_generate_welcome_message_requires_document(sample_user, sample_project):
    client = APIClient()
    client.force_authenticate(user=sample_user)

    response = client.post(
        "/api/documents/welcome-message/generate/",
        data={"project_id": sample_project.id},
        format="json",
    )

    assert response.status_code == 400
    assert "Upload at least one document" in response.data["error"]


@requires_postgres
@pytest.mark.django_db
def test_generate_welcome_message_falls_back_if_llm_fails(sample_user, sample_project, monkeypatch):
    client = APIClient()
    client.force_authenticate(user=sample_user)

    Document.objects.create(
        title="Delivery Policy",
        content="Delivery windows, regions, and lead times.",
        project=sample_project,
        processed=True,
    )

    def _raise(_project):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr("apps.documents.views.get_llm_client_for_project", _raise)

    response = client.post(
        "/api/documents/welcome-message/generate/",
        data={"project_id": sample_project.id, "max_length": 180},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["generated_with_fallback"] is True
    assert response.data["message"]
    assert len(response.data["message"]) <= 180
