from django.urls import path

from .views import LeadDetailView, LeadListView

urlpatterns = [
    path("", LeadListView.as_view(), name="lead-list"),
    path("<uuid:lead_id>/", LeadDetailView.as_view(), name="lead-detail"),
]
