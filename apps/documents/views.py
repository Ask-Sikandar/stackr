from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.conf import settings

from apps.accounts.access import get_project_for_user
from services.factory import get_llm_client_for_project
from services.metering import record_usage_event
from .models import Chunk, Document, IngestionJob, IngestionStatus
from .serializers import ChunkSerializer, DocumentListSerializer, DocumentSerializer, IngestionJobSerializer
from .tasks import run_ingestion_job, warm_ingestion_worker


WELCOME_MESSAGE_DEFAULT_MAX_LENGTH = 280
WELCOME_MESSAGE_MIN_LENGTH = 120
WELCOME_MESSAGE_MAX_ALLOWED = 400
WELCOME_MESSAGE_DOCUMENT_LIMIT = 4
WELCOME_MESSAGE_EXCERPT_LIMIT = 1200


def _coerce_welcome_max_length(raw_value) -> int:
    if raw_value is None:
        return WELCOME_MESSAGE_DEFAULT_MAX_LENGTH
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return WELCOME_MESSAGE_DEFAULT_MAX_LENGTH
    return max(WELCOME_MESSAGE_MIN_LENGTH, min(parsed, WELCOME_MESSAGE_MAX_ALLOWED))


def _truncate_sentence(text: str, max_length: int) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= max_length:
        return cleaned

    cropped = cleaned[: max_length + 1]
    if " " in cropped:
        cropped = cropped.rsplit(" ", 1)[0]
    cropped = cropped.rstrip(" ,.;:-")
    if not cropped:
        return ""
    return f"{cropped}."


def _fallback_welcome_message(source_documents: list[Document], max_length: int) -> str:
    titles = [doc.title.strip() for doc in source_documents if (doc.title or "").strip()]
    topic_fragment = ", ".join(titles[:2]) if titles else "your uploaded documents"

    fallback = (
        f"Hi! I can help answer questions based on {topic_fragment}. "
        "I can guide you on details, policies, pricing, and comparisons from your uploaded knowledge. "
        "What would you like to explore first?"
    )
    return _truncate_sentence(fallback, max_length)


def _normalize_welcome_message(raw: str, max_length: int, source_documents: list[Document]) -> str:
    cleaned = " ".join((raw or "").replace("\n", " ").split()).strip(" \t\n\r\"'`")
    if not cleaned:
        return _fallback_welcome_message(source_documents, max_length)

    if not cleaned.lower().startswith(("hi", "hello", "welcome")):
        cleaned = f"Hi! {cleaned[0].upper()}{cleaned[1:] if len(cleaned) > 1 else ''}"

    if "?" not in cleaned:
        cleaned = f"{cleaned.rstrip('. ')} What would you like to ask first?"

    normalized = _truncate_sentence(cleaned, max_length)
    if len(normalized) < 40:
        return _fallback_welcome_message(source_documents, max_length)
    return normalized


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

        if document.project_id is not None:
            record_usage_event(
                event_type="ingestion.queued",
                organization_id=document.project.organization_id,
                project_id=document.project_id,
                quantity=1,
                metadata={
                    "document_id": document.id,
                    "job_id": str(job.job_id),
                    "content_chars": len(document.content or ""),
                },
            )

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


class GenerateWelcomeMessageView(APIView):
    """POST /api/documents/welcome-message/generate/ — create project welcome text from uploaded docs."""

    def post(self, request: Request) -> Response:
        project_id = request.data.get("project_id")
        if project_id is None:
            raise ValidationError({"project_id": "This field is required."})

        try:
            project = get_project_for_user(request.user, int(project_id))
        except ValueError as exc:
            raise ValidationError({"project_id": "Invalid project id."}) from exc

        max_length = _coerce_welcome_max_length(request.data.get("max_length"))

        processed_documents = list(
            Document.objects.filter(project=project, processed=True)
            .order_by("-uploaded_at")[:WELCOME_MESSAGE_DOCUMENT_LIMIT]
        )
        source_documents = processed_documents
        used_processed_documents = True

        if not source_documents:
            source_documents = list(
                Document.objects.filter(project=project)
                .order_by("-uploaded_at")[:WELCOME_MESSAGE_DOCUMENT_LIMIT]
            )
            used_processed_documents = False

        if not source_documents:
            return Response(
                {"error": "Upload at least one document before generating a welcome message."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doc_summaries: list[str] = []
        for doc in source_documents:
            title = (doc.title or "").strip() or "Untitled"
            excerpt = (doc.content or "").strip()[:WELCOME_MESSAGE_EXCERPT_LIMIT]
            doc_summaries.append(f"- {title}: {excerpt}")

        prompt = (
            "Write a sensible welcome message for a B2B sales assistant chat interface.\n"
            f"Output length must be <= {max_length} characters.\n"
            "Requirements:\n"
            "- 2 to 3 concise sentences\n"
            "- Sound professional, friendly, and confident\n"
            "- Mention that the assistant can answer based on uploaded project documents\n"
            "- Include examples of topics inferred from the provided documents\n"
            "- End with one clear question inviting the user to ask\n"
            "- No markdown, no bullets, no quotes, no fake claims\n\n"
            "Project documents:\n"
            f"{'\n'.join(doc_summaries)}"
        )

        generated_with_fallback = False
        try:
            llm_client = get_llm_client_for_project(project)
            raw_message = llm_client.complete(prompt)
        except Exception:
            raw_message = ""
            generated_with_fallback = True

        message = _normalize_welcome_message(raw_message, max_length, source_documents)

        record_usage_event(
            event_type="welcome_message.generated",
            organization_id=project.organization_id,
            project_id=project.id,
            quantity=1,
            metadata={
                "max_length": max_length,
                "source_document_count": len(source_documents),
                "used_processed_documents": used_processed_documents,
                "generated_with_fallback": generated_with_fallback,
                "output_length": len(message),
            },
        )

        return Response(
            {
                "message": message,
                "max_length": max_length,
                "source_document_count": len(source_documents),
                "used_processed_documents": used_processed_documents,
                "generated_with_fallback": generated_with_fallback,
            }
        )
