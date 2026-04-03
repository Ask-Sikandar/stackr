import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Membership, MembershipRole, Organization, OrganizationLLMKey, Project
from tests.conftest import requires_postgres


@requires_postgres
@pytest.mark.django_db
def test_register_creates_user_and_organization():
    client = APIClient()

    response = client.post(
        "/api/accounts/register/",
        {
            "email": "founder@example.com",
            "password": "securepass123",
            "full_name": "Founder",
            "organization_name": "Founder Org",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["access"]
    assert response.data["refresh"]

    org = Organization.objects.get(id=response.data["organization_id"])
    assert org.name == "Founder Org"
    assert Membership.objects.filter(organization=org, role=MembershipRole.OWNER).exists()


@requires_postgres
@pytest.mark.django_db
def test_project_creation_requires_membership(sample_user, sample_organization):
    client = APIClient()
    client.force_authenticate(user=sample_user)

    response = client.post(
        "/api/accounts/projects/",
        {"organization_id": sample_organization.id, "name": "Sales Assistant"},
        format="json",
    )

    assert response.status_code == 201
    assert Project.objects.filter(name="Sales Assistant", organization=sample_organization).exists()


@requires_postgres
@pytest.mark.django_db
def test_organization_list_returns_user_orgs(sample_user, sample_organization):
    client = APIClient()
    client.force_authenticate(user=sample_user)

    response = client.get("/api/accounts/organizations/")

    assert response.status_code == 200
    ids = [row["id"] for row in response.data]
    assert sample_organization.id in ids


@requires_postgres
@pytest.mark.django_db
def test_upsert_organization_llm_key(sample_user, sample_organization):
    client = APIClient()
    client.force_authenticate(user=sample_user)

    response = client.post(
        f"/api/accounts/organizations/{sample_organization.id}/llm-keys/",
        {"provider": "openai", "api_key": "org-private-1234", "is_active": True},
        format="json",
    )

    assert response.status_code == 201
    key = OrganizationLLMKey.objects.get(organization=sample_organization, provider="openai")
    assert key.api_key == "org-private-1234"


@requires_postgres
@pytest.mark.django_db
def test_project_patch_updates_provider_settings(sample_user, sample_project):
    client = APIClient()
    client.force_authenticate(user=sample_user)

    response = client.patch(
        f"/api/accounts/projects/{sample_project.id}/",
        {
            "llm_primary_provider": "openai",
            "llm_backup_provider": "gemini",
            "custom_instructions": "Be concise and professional.",
        },
        format="json",
    )

    assert response.status_code == 200
    sample_project.refresh_from_db()
    assert sample_project.llm_primary_provider == "openai"
    assert sample_project.llm_backup_provider == "gemini"
    assert sample_project.custom_instructions == "Be concise and professional."
