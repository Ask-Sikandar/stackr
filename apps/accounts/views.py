from django.db import transaction
from django.db.models import Count, Sum
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LLMProvider, Membership, MembershipRole, Organization, OrganizationLLMKey, Project, UsageEvent
from .serializers import (
    OrganizationCreateSerializer,
    OrganizationLLMKeyRotateSerializer,
    OrganizationLLMKeySerializer,
    OrganizationLLMKeyUpsertSerializer,
    OrganizationSerializer,
    OrganizationUpdateSerializer,
    ProjectCreateSerializer,
    ProjectSerializer,
    ProjectUpdateSerializer,
    RegisterSerializer,
    UsageEventSerializer,
)


def _get_organization_for_user(user, organization_id: int) -> Organization | None:
    return (
        Organization.objects.filter(
            id=organization_id,
            memberships__user=user,
            memberships__is_active=True,
        )
        .distinct()
        .first()
    )


def _get_project_for_user(user, project_id: int) -> Project | None:
    return (
        Project.objects.filter(
            id=project_id,
            organization__memberships__user=user,
            organization__memberships__is_active=True,
        )
        .distinct()
        .first()
    )


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        org = result["organization"]
        return Response(
            {
                "user_id": result["user"].id,
                "organization_id": org.id if org else None,
                "access": result["access"],
                "refresh": result["refresh"],
            },
            status=status.HTTP_201_CREATED,
        )


class OrganizationListCreateView(APIView):
    def get(self, request: Request) -> Response:
        orgs = Organization.objects.filter(memberships__user=request.user, memberships__is_active=True).distinct()
        serializer = OrganizationSerializer(orgs, many=True)
        return Response(serializer.data)

    def post(self, request: Request) -> Response:
        serializer = OrganizationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            org = Organization.objects.create(
                name=serializer.validated_data["name"],
                owner=request.user,
                use_private_llm_credentials=serializer.validated_data["use_private_llm_credentials"],
                allow_platform_fallback=serializer.validated_data["allow_platform_fallback"],
                custom_instructions=serializer.validated_data["custom_instructions"],
            )
            Membership.objects.create(user=request.user, organization=org, role=MembershipRole.OWNER)

        out = OrganizationSerializer(org)
        return Response(out.data, status=status.HTTP_201_CREATED)


class OrganizationDetailView(APIView):
    def patch(self, request: Request, organization_id: int) -> Response:
        org = _get_organization_for_user(request.user, organization_id)
        if org is None:
            return Response({"error": "Organization not found or access denied."}, status=status.HTTP_403_FORBIDDEN)

        serializer = OrganizationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(org, field, value)
        org.save(update_fields=list(serializer.validated_data.keys()))
        return Response(OrganizationSerializer(org).data)


class ProjectListCreateView(APIView):
    def get(self, request: Request) -> Response:
        org_id = request.query_params.get("organization_id")
        projects = Project.objects.filter(
            organization__memberships__user=request.user,
            organization__memberships__is_active=True,
        )
        if org_id:
            projects = projects.filter(organization_id=org_id)
        serializer = ProjectSerializer(projects.distinct(), many=True)
        return Response(serializer.data)

    def post(self, request: Request) -> Response:
        serializer = ProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        org = (
            _get_organization_for_user(request.user, serializer.validated_data["organization_id"])
        )
        if org is None:
            return Response({"error": "Organization not found or access denied."}, status=status.HTTP_403_FORBIDDEN)

        project = Project.objects.create(
            organization=org,
            name=serializer.validated_data["name"],
            llm_primary_provider=serializer.validated_data["llm_primary_provider"],
            llm_backup_provider=serializer.validated_data["llm_backup_provider"],
            custom_instructions=serializer.validated_data["custom_instructions"],
        )
        out = ProjectSerializer(project)
        return Response(out.data, status=status.HTTP_201_CREATED)


class ProjectDetailView(APIView):
    def patch(self, request: Request, project_id: int) -> Response:
        project = _get_project_for_user(request.user, project_id)
        if project is None:
            return Response({"error": "Project not found or access denied."}, status=status.HTTP_403_FORBIDDEN)

        serializer = ProjectUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(project, field, value)
        project.save(update_fields=list(serializer.validated_data.keys()))
        return Response(ProjectSerializer(project).data)


class OrganizationLLMKeyListUpsertView(APIView):
    def get(self, request: Request, organization_id: int) -> Response:
        org = _get_organization_for_user(request.user, organization_id)
        if org is None:
            return Response({"error": "Organization not found or access denied."}, status=status.HTTP_403_FORBIDDEN)

        keys = OrganizationLLMKey.objects.filter(organization=org)
        serializer = OrganizationLLMKeySerializer(keys, many=True)
        return Response(serializer.data)

    def post(self, request: Request, organization_id: int) -> Response:
        org = _get_organization_for_user(request.user, organization_id)
        if org is None:
            return Response({"error": "Organization not found or access denied."}, status=status.HTTP_403_FORBIDDEN)

        serializer = OrganizationLLMKeyUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        key_obj, _ = OrganizationLLMKey.objects.get_or_create(
            organization=org,
            provider=serializer.validated_data["provider"],
        )
        key_obj.set_api_key(serializer.validated_data["api_key"])
        key_obj.is_active = serializer.validated_data["is_active"]
        key_obj.save()

        out = OrganizationLLMKeySerializer(key_obj)
        return Response(out.data, status=status.HTTP_201_CREATED)


def _normalize_provider(provider: str) -> str | None:
    normalized = (provider or "").strip().lower()
    allowed = {choice.value for choice in LLMProvider}
    if normalized not in allowed:
        return None
    return normalized


class OrganizationLLMKeyRotateView(APIView):
    def post(self, request: Request, organization_id: int, provider: str) -> Response:
        org = _get_organization_for_user(request.user, organization_id)
        if org is None:
            return Response({"error": "Organization not found or access denied."}, status=status.HTTP_403_FORBIDDEN)

        normalized_provider = _normalize_provider(provider)
        if normalized_provider is None:
            return Response({"error": "Unsupported provider."}, status=status.HTTP_400_BAD_REQUEST)

        key_obj = OrganizationLLMKey.objects.filter(organization=org, provider=normalized_provider).first()
        if key_obj is None:
            return Response({"error": "Provider key not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrganizationLLMKeyRotateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        key_obj.set_api_key(serializer.validated_data["api_key"])
        key_obj.is_active = True
        key_obj.save(update_fields=["api_key", "is_active", "updated_at"])

        return Response(OrganizationLLMKeySerializer(key_obj).data)


class OrganizationLLMKeyRevokeView(APIView):
    def post(self, request: Request, organization_id: int, provider: str) -> Response:
        org = _get_organization_for_user(request.user, organization_id)
        if org is None:
            return Response({"error": "Organization not found or access denied."}, status=status.HTTP_403_FORBIDDEN)

        normalized_provider = _normalize_provider(provider)
        if normalized_provider is None:
            return Response({"error": "Unsupported provider."}, status=status.HTTP_400_BAD_REQUEST)

        key_obj = OrganizationLLMKey.objects.filter(organization=org, provider=normalized_provider).first()
        if key_obj is None:
            return Response({"error": "Provider key not found."}, status=status.HTTP_404_NOT_FOUND)

        key_obj.is_active = False
        key_obj.save(update_fields=["is_active", "updated_at"])

        return Response(OrganizationLLMKeySerializer(key_obj).data)


class OrganizationUsageEventsView(APIView):
    def get(self, request: Request, organization_id: int) -> Response:
        org = _get_organization_for_user(request.user, organization_id)
        if org is None:
            return Response({"error": "Organization not found or access denied."}, status=status.HTTP_403_FORBIDDEN)

        events = UsageEvent.objects.filter(organization=org)

        project_id_raw = request.query_params.get("project_id")
        project_id: int | None = None
        if project_id_raw:
            try:
                project_id = int(project_id_raw)
            except (TypeError, ValueError):
                return Response({"error": "Invalid project_id."}, status=status.HTTP_400_BAD_REQUEST)

            if not org.projects.filter(id=project_id).exists():
                return Response({"error": "Project not found in organization."}, status=status.HTTP_404_NOT_FOUND)
            events = events.filter(project_id=project_id)

        event_type = (request.query_params.get("event_type") or "").strip()
        if event_type:
            events = events.filter(event_type=event_type)

        since_raw = (request.query_params.get("since") or "").strip()
        if since_raw:
            since_dt = parse_datetime(since_raw)
            if since_dt is None:
                return Response({"error": "Invalid since datetime."}, status=status.HTTP_400_BAD_REQUEST)
            events = events.filter(created_at__gte=since_dt)

        until_raw = (request.query_params.get("until") or "").strip()
        if until_raw:
            until_dt = parse_datetime(until_raw)
            if until_dt is None:
                return Response({"error": "Invalid until datetime."}, status=status.HTTP_400_BAD_REQUEST)
            events = events.filter(created_at__lte=until_dt)

        totals = list(
            events.values("event_type")
            .annotate(total_quantity=Sum("quantity"), event_count=Count("id"))
            .order_by("event_type")
        )

        limit_raw = request.query_params.get("limit", "100")
        try:
            limit = max(1, min(int(limit_raw), 500))
        except (TypeError, ValueError):
            return Response({"error": "Invalid limit value."}, status=status.HTTP_400_BAD_REQUEST)

        recent = events.select_related("project").order_by("-created_at")[:limit]
        serialized = UsageEventSerializer(recent, many=True)

        return Response(
            {
                "organization_id": org.id,
                "project_id": project_id,
                "count": events.count(),
                "totals": totals,
                "events": serialized.data,
            }
        )
