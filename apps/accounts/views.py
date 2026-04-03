from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Membership, MembershipRole, Organization, OrganizationLLMKey, Project
from .serializers import (
    OrganizationCreateSerializer,
    OrganizationLLMKeySerializer,
    OrganizationLLMKeyUpsertSerializer,
    OrganizationSerializer,
    OrganizationUpdateSerializer,
    ProjectCreateSerializer,
    ProjectSerializer,
    ProjectUpdateSerializer,
    RegisterSerializer,
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

        key_obj, _ = OrganizationLLMKey.objects.update_or_create(
            organization=org,
            provider=serializer.validated_data["provider"],
            defaults={
                "api_key": serializer.validated_data["api_key"],
                "is_active": serializer.validated_data["is_active"],
            },
        )

        out = OrganizationLLMKeySerializer(key_obj)
        return Response(out.data, status=status.HTTP_201_CREATED)
