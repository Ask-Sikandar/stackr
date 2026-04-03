from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import OrganizationListCreateView, ProjectListCreateView, RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", TokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("organizations/", OrganizationListCreateView.as_view(), name="organization-list-create"),
    path("projects/", ProjectListCreateView.as_view(), name="project-list-create"),
]
