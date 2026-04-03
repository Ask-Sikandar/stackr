from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import LLMProvider, Membership, MembershipRole, Organization, OrganizationLLMKey, Project


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
        fields = [
            "id",
            "name",
            "owner_id",
            "use_private_llm_credentials",
            "allow_platform_fallback",
            "created_at",
        ]
        read_only_fields = ["owner_id", "created_at"]


class ProjectSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(source="organization.id", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "organization_id",
            "llm_primary_provider",
            "llm_backup_provider",
            "custom_instructions",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class OrganizationCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    use_private_llm_credentials = serializers.BooleanField(default=False)
    allow_platform_fallback = serializers.BooleanField(default=True)


class OrganizationUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    use_private_llm_credentials = serializers.BooleanField(required=False)
    allow_platform_fallback = serializers.BooleanField(required=False)


class ProjectCreateSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    name = serializers.CharField(max_length=255)
    llm_primary_provider = serializers.ChoiceField(choices=LLMProvider.choices, required=False, default=LLMProvider.OLLAMA)
    llm_backup_provider = serializers.ChoiceField(choices=LLMProvider.choices, required=False, allow_blank=True, default="")
    custom_instructions = serializers.CharField(required=False, allow_blank=True, default="")


class ProjectUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    llm_primary_provider = serializers.ChoiceField(choices=LLMProvider.choices, required=False)
    llm_backup_provider = serializers.ChoiceField(choices=LLMProvider.choices, required=False, allow_blank=True)
    custom_instructions = serializers.CharField(required=False, allow_blank=True)


class OrganizationLLMKeySerializer(serializers.ModelSerializer):
    key_hint = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationLLMKey
        fields = ["id", "provider", "is_active", "key_hint", "created_at", "updated_at"]

    @staticmethod
    def get_key_hint(obj: OrganizationLLMKey) -> str:
        if len(obj.api_key) < 4:
            return "****"
        return f"****{obj.api_key[-4:]}"


class OrganizationLLMKeyUpsertSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=LLMProvider.choices)
    api_key = serializers.CharField(min_length=8, max_length=255)
    is_active = serializers.BooleanField(default=True)
