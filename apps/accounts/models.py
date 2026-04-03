from django.conf import settings
from django.db import models

from .crypto import decrypt_secret, encrypt_secret


class MembershipRole(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    MEMBER = "member", "Member"
    VIEWER = "viewer", "Viewer"


class LLMProvider(models.TextChoices):
    OLLAMA = "ollama", "Ollama"
    OPENAI = "openai", "OpenAI"
    GEMINI = "gemini", "Gemini"


class Organization(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="owned_organizations",
        on_delete=models.CASCADE,
    )
    use_private_llm_credentials = models.BooleanField(default=False)
    allow_platform_fallback = models.BooleanField(default=True)
    custom_instructions = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="organization_memberships",
        on_delete=models.CASCADE,
    )
    organization = models.ForeignKey(
        Organization,
        related_name="memberships",
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=20, choices=MembershipRole.choices, default=MembershipRole.MEMBER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "organization")]
        ordering = ["organization", "user"]

    def __str__(self) -> str:
        return f"{self.user} -> {self.organization} ({self.role})"


class Project(models.Model):
    organization = models.ForeignKey(
        Organization,
        related_name="projects",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=255)
    llm_primary_provider = models.CharField(
        max_length=20,
        choices=LLMProvider.choices,
        default=LLMProvider.OLLAMA,
    )
    llm_backup_provider = models.CharField(
        max_length=20,
        choices=LLMProvider.choices,
        blank=True,
        default="",
    )
    custom_instructions = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("organization", "name")]
        ordering = ["organization", "name"]

    def __str__(self) -> str:
        return f"{self.organization.name} / {self.name}"


class OrganizationLLMKey(models.Model):
    organization = models.ForeignKey(
        Organization,
        related_name="llm_keys",
        on_delete=models.CASCADE,
    )
    provider = models.CharField(max_length=20, choices=LLMProvider.choices)
    api_key = models.CharField(max_length=1024)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("organization", "provider")]
        ordering = ["organization", "provider"]

    def set_api_key(self, raw_api_key: str) -> None:
        self.api_key = encrypt_secret(raw_api_key)

    def get_api_key(self) -> str:
        return decrypt_secret(self.api_key)

    def get_key_hint(self) -> str:
        plain = self.get_api_key()
        if len(plain) < 4:
            return "****"
        return f"****{plain[-4:]}"

    def __str__(self) -> str:
        return f"{self.organization.name} / {self.provider}"


class UsageEvent(models.Model):
    organization = models.ForeignKey(
        Organization,
        related_name="usage_events",
        on_delete=models.CASCADE,
    )
    project = models.ForeignKey(
        Project,
        related_name="usage_events",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=64, db_index=True)
    quantity = models.IntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "event_type"]),
            models.Index(fields=["project", "event_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.organization_id}:{self.project_id}:{self.event_type}:{self.quantity}"
