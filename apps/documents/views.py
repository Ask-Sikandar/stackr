from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.conf import settings

from apps.accounts.access import get_project_for_user
from .models import Chunk, Document, IngestionJob, IngestionStatus
from .serializers import ChunkSerializer, DocumentListSerializer, DocumentSerializer, IngestionJobSerializer
from .tasks import run_ingestion_job, warm_ingestion_worker


class DocumentListCreateView(ListCreateAPIView):
    """GET /api/documents/  — list all documents (lightweight)
    POST /api/documents/ — upload a new document"""

    def get_queryset(self):
        return Document.objects.filter(
            project__organization__memberships__user=self.request.user,
            project__organization__memberships__is_active=True,
        ).distinct()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return DocumentListSerializer
        return DocumentSerializer

    def perform_create(self, serializer):
        project_id = self.request.data.get("project_id")
        if project_id is None:
            raise ValidationError({"project_id": "This field is required."})
        try:
            project = get_project_for_user(self.request.user, int(project_id))
        except ValueError as exc:
            raise ValidationError({"project_id": "Invalid project id."}) from exc

        document = serializer.save(project=project)
        if bool(getattr(settings, "INGESTION_WARM_ON_UPLOAD", True)):
            try:
                warm_ingestion_worker.delay()
            except Exception:
                # Warm failures should never block upload UX.
                pass
        return document


class DocumentDetailView(RetrieveAPIView):
    """GET /api/documents/<id>/ — full document detail"""

    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(
            project__organization__memberships__user=self.request.user,
            project__organization__memberships__is_active=True,
        ).distinct()


class IngestDocumentView(APIView):
    """POST /api/documents/<id>/ingest/ — trigger chunking + embedding pipeline"""

    def post(self, request: Request, pk: int) -> Response:
        try:
            document = Document.objects.filter(
                pk=pk,
                project__organization__memberships__user=request.user,
                project__organization__memberships__is_active=True,
            ).distinct().get()
        except Document.DoesNotExist:
            return Response({"error": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        existing = document.ingestion_jobs.filter(
            status__in=[IngestionStatus.QUEUED, IngestionStatus.RUNNING]
        ).first()
        if existing is not None:
            serializer = IngestionJobSerializer(existing)
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

        with transaction.atomic():
            job = IngestionJob.objects.create(document=document, status=IngestionStatus.QUEUED)

        try:
            task_result = run_ingestion_job.delay(str(job.job_id))
        except Exception as exc:
            job.status = IngestionStatus.FAILED
            job.error_message = str(exc)
            job.save(update_fields=["status", "error_message"])
            return Response(
                {"error": "Failed to enqueue ingestion job.", "detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        job.task_id = str(task_result.id)
        job.save(update_fields=["task_id"])

        serializer = IngestionJobSerializer(job)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


class ChunkListView(APIView):
    """GET /api/documents/<id>/chunks/ — list chunks for a document"""

    def get(self, request: Request, pk: int) -> Response:
        try:
            document = Document.objects.filter(
                pk=pk,
                project__organization__memberships__user=request.user,
                project__organization__memberships__is_active=True,
            ).distinct().get()
        except Document.DoesNotExist:
            return Response({"error": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        chunks = Chunk.objects.filter(document=document)
        serializer = ChunkSerializer(chunks, many=True)
        return Response(serializer.data)


class IngestionJobStatusView(APIView):
    """GET /api/documents/ingest-jobs/<job_id>/ — retrieve async ingestion status"""

    def get(self, request: Request, job_id) -> Response:
        try:
            job = IngestionJob.objects.select_related("document").filter(
                job_id=job_id,
                document__project__organization__memberships__user=request.user,
                document__project__organization__memberships__is_active=True,
            ).distinct().get()
        except IngestionJob.DoesNotExist:
            return Response({"error": "Ingestion job not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = IngestionJobSerializer(job)
        return Response(serializer.data)


class IngestionWarmView(APIView):
    """POST /api/documents/ingestion/warm/ — opportunistically warm ingestion worker."""

    def post(self, request: Request) -> Response:
        try:
            result = warm_ingestion_worker.delay()
        except Exception as exc:
            return Response(
                {"error": "Failed to enqueue warm task.", "detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({"status": "queued", "task_id": str(result.id)}, status=status.HTTP_202_ACCEPTED)
