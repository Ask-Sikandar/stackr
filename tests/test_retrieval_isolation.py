import pytest

from apps.accounts.models import Membership, MembershipRole, Organization, Project
from apps.documents.models import Chunk, Document
from services.mocks import MockEmbedder
from services.retrieval import PgVectorRetriever
from tests.conftest import requires_postgres


@requires_postgres
@pytest.mark.django_db
def test_retriever_filters_by_project_id(sample_user):
    embedder = MockEmbedder()
    retriever = PgVectorRetriever(embedder=embedder)

    org = Organization.objects.create(name="Scoped Org", owner=sample_user)
    Membership.objects.create(user=sample_user, organization=org, role=MembershipRole.OWNER)
    p1 = Project.objects.create(organization=org, name="Project One")
    p2 = Project.objects.create(organization=org, name="Project Two")

    doc1 = Document.objects.create(title="P1 Pricing", content="Project one pricing", project=p1)
    doc2 = Document.objects.create(title="P2 Pricing", content="Project two pricing", project=p2)

    Chunk.objects.create(
        document=doc1,
        content="P1 chunk content",
        embedding=embedder.embed("pricing"),
        chunk_index=0,
        metadata={},
    )
    Chunk.objects.create(
        document=doc2,
        content="P2 chunk content",
        embedding=embedder.embed("pricing"),
        chunk_index=0,
        metadata={},
    )

    scoped = retriever.retrieve("pricing", top_k=10, project_id=p1.id)

    assert scoped
    assert all(chunk.document_title == "P1 Pricing" for chunk in scoped)


@requires_postgres
@pytest.mark.django_db
def test_retriever_without_project_filter_can_return_all_projects(sample_user):
    embedder = MockEmbedder()
    retriever = PgVectorRetriever(embedder=embedder)

    org = Organization.objects.create(name="Global Org", owner=sample_user)
    Membership.objects.create(user=sample_user, organization=org, role=MembershipRole.OWNER)
    p1 = Project.objects.create(organization=org, name="Alpha")
    p2 = Project.objects.create(organization=org, name="Beta")

    doc1 = Document.objects.create(title="Alpha Doc", content="Alpha content", project=p1)
    doc2 = Document.objects.create(title="Beta Doc", content="Beta content", project=p2)

    Chunk.objects.create(
        document=doc1,
        content="alpha chunk",
        embedding=embedder.embed("availability"),
        chunk_index=0,
        metadata={},
    )
    Chunk.objects.create(
        document=doc2,
        content="beta chunk",
        embedding=embedder.embed("availability"),
        chunk_index=0,
        metadata={},
    )

    unscoped = retriever.retrieve("availability", top_k=10)
    titles = {chunk.document_title for chunk in unscoped}

    assert "Alpha Doc" in titles
    assert "Beta Doc" in titles
