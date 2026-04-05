from django.urls import path

from .views import (
    ChunkListView,
    DocumentDetailView,
    DocumentListCreateView,
    GenerateWelcomeMessageView,
    IngestionJobStatusView,
    IngestionWarmView,
    IngestDocumentView,
)

urlpatterns = [
    path("", DocumentListCreateView.as_view(), name="document-list-create"),
    path("welcome-message/generate/", GenerateWelcomeMessageView.as_view(), name="generate-welcome-message"),
    path("ingestion/warm/", IngestionWarmView.as_view(), name="ingestion-warm"),
    path("ingest-jobs/<uuid:job_id>/", IngestionJobStatusView.as_view(), name="ingest-job-status"),
    path("<int:pk>/", DocumentDetailView.as_view(), name="document-detail"),
    path("<int:pk>/ingest/", IngestDocumentView.as_view(), name="document-ingest"),
    path("<int:pk>/chunks/", ChunkListView.as_view(), name="document-chunks"),
]
