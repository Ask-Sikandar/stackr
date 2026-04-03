from django.contrib import admin

from .models import Membership, Organization, OrganizationLLMKey, Project


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "owner",
        "use_private_llm_credentials",
        "allow_platform_fallback",
        "created_at",
    ]
    search_fields = ["name", "owner__username", "owner__email"]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "organization", "role", "is_active"]
    list_filter = ["role", "is_active"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "llm_primary_provider", "llm_backup_provider", "created_at"]
    list_filter = ["organization"]


@admin.register(OrganizationLLMKey)
class OrganizationLLMKeyAdmin(admin.ModelAdmin):
    list_display = ["organization", "provider", "is_active", "updated_at"]
    list_filter = ["provider", "is_active"]
