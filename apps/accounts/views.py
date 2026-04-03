from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Membership, MembershipRole, Organization, Project
from .serializers import (
    OrganizationCreateSerializer,
    OrganizationSerializer,
    ProjectCreateSerializer,
    ProjectSerializer,
    RegisterSerializer,
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
            org = Organization.objects.create(name=serializer.validated_data["name"], owner=request.user)
            Membership.objects.create(user=request.user, organization=org, role=MembershipRole.OWNER)

        out = OrganizationSerializer(org)
        return Response(out.data, status=status.HTTP_201_CREATED)


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
            Organization.objects.filter(
                id=serializer.validated_data["organization_id"],
                memberships__user=request.user,
                memberships__is_active=True,
            )
            .distinct()
            .first()
        )
        if org is None:
            return Response({"error": "Organization not found or access denied."}, status=status.HTTP_403_FORBIDDEN)

        project = Project.objects.create(
            organization=org,
            name=serializer.validated_data["name"],
        )
        out = ProjectSerializer(project)
        return Response(out.data, status=status.HTTP_201_CREATED)
