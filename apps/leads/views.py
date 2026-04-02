from rest_framework.generics import ListAPIView, RetrieveAPIView

from .models import Lead
from .serializers import LeadListSerializer, LeadSerializer


class LeadListView(ListAPIView):
    """GET /api/leads/ — list all leads ordered by score desc (dashboard feed)"""

    queryset = Lead.objects.prefetch_related("conversations__messages", "intent_events").all()
    serializer_class = LeadListSerializer


class LeadDetailView(RetrieveAPIView):
    """GET /api/leads/<lead_id>/ — full lead detail with intent timeline"""

    queryset = Lead.objects.prefetch_related("conversations__messages", "intent_events").all()
    serializer_class = LeadSerializer
    lookup_field = "lead_id"
