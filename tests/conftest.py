"""
Shared pytest fixtures.

DB tests (marked @pytest.mark.django_db) require a running PostgreSQL with
the pgvector extension.  If no DB is reachable, they are automatically skipped
so the pure unit tests can still run in any environment (CI, local dev without Docker).

Pure unit tests (intent classification, embedding mocks, agent, prompt builder)
never touch the DB and always run.
"""
import pytest
from django.contrib.auth.models import User

from apps.accounts.models import Membership, MembershipRole, Organization, Project

from services import factory as svc_factory


def _postgres_available() -> bool:
    """Return True if the test PostgreSQL is reachable."""
    try:
        import psycopg

        conn = psycopg.connect(
            host="localhost",
            port=5432,
            dbname="postgres",
            user="memox",
            password="memox",
            connect_timeout=2,
        )
        conn.close()
        return True
    except Exception:
        return False


# Evaluate once at collection time
_POSTGRES_AVAILABLE = _postgres_available()

requires_postgres = pytest.mark.skipif(
    not _POSTGRES_AVAILABLE,
    reason="PostgreSQL not available (start via docker-compose or set up a local DB)",
)


@pytest.fixture(autouse=True)
def reset_service_cache():
    """Clear lru_cache singletons before each test so mock settings apply cleanly."""
    svc_factory.reset_cache()
    yield
    svc_factory.reset_cache()


@pytest.fixture
def sample_document(db):
    from apps.documents.models import Document

    return Document.objects.create(
        title="Pricing Sheet",
        content=(
            "# Pricing\n\n"
            "40ft standard container: $3,850. 20ft standard: $2,100.\n\n"
            "One-trip 40ft: $5,900. Grade B 20ft: $1,600.\n\n"
            "## Deposit\n\n"
            "A 20% deposit is required to reserve a unit. "
            "Balance is due before delivery. We accept wire transfer and ACH.\n\n"
            "## Bulk Discount\n\n"
            "- 2–4 units: 5% off\n"
            "- 5–9 units: 10% off\n"
            "- 10+ units: 15% off"
        ),
    )


@pytest.fixture
def sample_user(db):
    return User.objects.create_user(
        username="owner@example.com",
        email="owner@example.com",
        password="testpass123",
    )


@pytest.fixture
def sample_organization(db, sample_user):
    org = Organization.objects.create(name="Acme Containers", owner=sample_user)
    Membership.objects.create(user=sample_user, organization=org, role=MembershipRole.OWNER)
    return org


@pytest.fixture
def sample_project(db, sample_organization):
    return Project.objects.create(organization=sample_organization, name="Default Project")


@pytest.fixture
def sample_lead(db):
    from apps.leads.models import Lead

    return Lead.objects.create()
