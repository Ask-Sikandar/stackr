from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.conf import settings

from .models import Chunk, Document, IngestionJob, IngestionStatus
from .serializers import ChunkSerializer, DocumentListSerializer, DocumentSerializer, IngestionJobSerializer
from .tasks import run_ingestion_job, warm_ingestion_worker


class DocumentListCreateView(ListCreateAPIView):
    """GET /api/documents/  — list all documents (lightweight)
    POST /api/documents/ — upload a new document"""

    queryset = Document.objects.all()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return DocumentListSerializer
        return DocumentSerializer

    def perform_create(self, serializer):
        document = serializer.save()
        if bool(getattr(settings, "INGESTION_WARM_ON_UPLOAD", True)):
            try:
                warm_ingestion_worker.delay()
            except Exception:
                # Warm failures should never block upload UX.
                pass
        return document


class DocumentDetailView(RetrieveAPIView):
    """GET /api/documents/<id>/ — full document detail"""

    queryset = Document.objects.all()
    serializer_class = DocumentSerializer


class IngestDocumentView(APIView):
    """POST /api/documents/<id>/ingest/ — trigger chunking + embedding pipeline"""

    def post(self, request: Request, pk: int) -> Response:
        try:
            document = Document.objects.get(pk=pk)
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
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            return Response({"error": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        chunks = Chunk.objects.filter(document=document)
        serializer = ChunkSerializer(chunks, many=True)
        return Response(serializer.data)


class IngestionJobStatusView(APIView):
    """GET /api/documents/ingest-jobs/<job_id>/ — retrieve async ingestion status"""

    def get(self, request: Request, job_id) -> Response:
        try:
            job = IngestionJob.objects.select_related("document").get(job_id=job_id)
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
