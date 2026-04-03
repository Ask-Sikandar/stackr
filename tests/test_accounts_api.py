import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Membership, MembershipRole, Organization, Project
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
