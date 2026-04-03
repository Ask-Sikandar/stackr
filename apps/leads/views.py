from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.exceptions import ValidationError

from apps.accounts.access import get_project_for_user

from .models import Lead
from .serializers import LeadListSerializer, LeadSerializer


class LeadListView(ListAPIView):
    """GET /api/leads/ — list all leads ordered by score desc (dashboard feed)"""

    serializer_class = LeadListSerializer

    def get_queryset(self):
        project_id = self.request.query_params.get("project_id")
        if project_id is None:
            raise ValidationError({"project_id": "This query parameter is required."})
        try:
            project = get_project_for_user(self.request.user, int(project_id))
        except ValueError as exc:
            raise ValidationError({"project_id": "Invalid project id."}) from exc
        return Lead.objects.filter(project=project).prefetch_related("conversations__messages", "intent_events")


class LeadDetailView(RetrieveAPIView):
    """GET /api/leads/<lead_id>/ — full lead detail with intent timeline"""

    serializer_class = LeadSerializer
    lookup_field = "lead_id"

    def get_queryset(self):
        project_id = self.request.query_params.get("project_id")
        if project_id is None:
            raise ValidationError({"project_id": "This query parameter is required."})
        try:
            project = get_project_for_user(self.request.user, int(project_id))
        except ValueError as exc:
            raise ValidationError({"project_id": "Invalid project id."}) from exc
        return Lead.objects.filter(project=project).prefetch_related("conversations__messages", "intent_events")
