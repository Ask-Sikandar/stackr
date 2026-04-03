from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    OrganizationDetailView,
    OrganizationLLMKeyListUpsertView,
    OrganizationListCreateView,
    ProjectDetailView,
    ProjectListCreateView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", TokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("organizations/", OrganizationListCreateView.as_view(), name="organization-list-create"),
    path("organizations/<int:organization_id>/", OrganizationDetailView.as_view(), name="organization-detail"),
    path(
        "organizations/<int:organization_id>/llm-keys/",
        OrganizationLLMKeyListUpsertView.as_view(),
        name="organization-llm-keys",
    ),
    path("projects/", ProjectListCreateView.as_view(), name="project-list-create"),
    path("projects/<int:project_id>/", ProjectDetailView.as_view(), name="project-detail"),
]
