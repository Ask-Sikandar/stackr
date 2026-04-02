from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/documents/", include("apps.documents.urls")),
    path("api/ai/", include("apps.ai.urls")),
    path("api/leads/", include("apps.leads.urls")),
]
