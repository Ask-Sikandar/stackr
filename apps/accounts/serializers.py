from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Membership, MembershipRole, Organization, Project


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    organization_name = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already in use.")
        return value

    def create(self, validated_data):
        email = validated_data["email"].strip().lower()
        password = validated_data["password"]
        full_name = validated_data.get("full_name", "").strip()
        org_name = validated_data.get("organization_name", "").strip()

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=full_name,
        )

        organization = None
        if org_name:
            organization = Organization.objects.create(name=org_name, owner=user)
            Membership.objects.create(user=user, organization=organization, role=MembershipRole.OWNER)

        refresh = RefreshToken.for_user(user)

        return {
            "user": user,
            "organization": organization,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "owner_id", "created_at"]
        read_only_fields = ["owner_id", "created_at"]


class ProjectSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(source="organization.id", read_only=True)

    class Meta:
        model = Project
        fields = ["id", "name", "organization_id", "created_at"]
        read_only_fields = ["created_at"]


class OrganizationCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)


class ProjectCreateSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    name = serializers.CharField(max_length=255)
