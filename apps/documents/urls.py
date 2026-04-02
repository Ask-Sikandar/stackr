from django.urls import path

from .views import ChunkListView, DocumentDetailView, DocumentListCreateView, IngestDocumentView

urlpatterns = [
    path("", DocumentListCreateView.as_view(), name="document-list-create"),
    path("<int:pk>/", DocumentDetailView.as_view(), name="document-detail"),
    path("<int:pk>/ingest/", IngestDocumentView.as_view(), name="document-ingest"),
    path("<int:pk>/chunks/", ChunkListView.as_view(), name="document-chunks"),
]
