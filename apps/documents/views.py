from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from services.ingestion import ingest_document

from .models import Chunk, Document
from .serializers import ChunkSerializer, DocumentListSerializer, DocumentSerializer


class DocumentListCreateView(ListCreateAPIView):
    """GET /api/documents/  — list all documents (lightweight)
    POST /api/documents/ — upload a new document"""

    queryset = Document.objects.all()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return DocumentListSerializer
        return DocumentSerializer


class DocumentDetailView(RetrieveAPIView):
    """GET /api/documents/<id>/ — full document detail"""

    queryset = Document.objects.all()
    serializer_class = DocumentSerializer


class IngestDocumentView(APIView):
    """POST /api/documents/<id>/ingest/ — trigger chunking + embedding pipeline"""

    def post(self, request: Request, pk: int) -> Response:
        try:
            chunks = ingest_document(pk)
        except Document.DoesNotExist:
            return Response({"error": "Document not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {
                "document_id": pk,
                "chunks_created": len(chunks),
                "status": "ingested",
            },
            status=status.HTTP_200_OK,
        )


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
