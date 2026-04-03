import pytest

from apps.accounts.models import OrganizationLLMKey
from services.factory import get_llm_client_for_project
from services.llm import FallbackLLMClient, OpenAILLMClient
from tests.conftest import requires_postgres


@requires_postgres
@pytest.mark.django_db
def test_private_mode_without_key_and_no_fallback_raises(sample_project):
    org = sample_project.organization
    org.use_private_llm_credentials = True
    org.allow_platform_fallback = False
    org.save(update_fields=["use_private_llm_credentials", "allow_platform_fallback"])

    sample_project.llm_primary_provider = "openai"
    sample_project.llm_backup_provider = ""
    sample_project.save(update_fields=["llm_primary_provider", "llm_backup_provider"])

    with pytest.raises(RuntimeError):
        get_llm_client_for_project(sample_project)


@requires_postgres
@pytest.mark.django_db
def test_private_mode_prefers_org_key(sample_project):
    org = sample_project.organization
    org.use_private_llm_credentials = True
    org.allow_platform_fallback = False
    org.save(update_fields=["use_private_llm_credentials", "allow_platform_fallback"])

    sample_project.llm_primary_provider = "openai"
    sample_project.llm_backup_provider = ""
    sample_project.save(update_fields=["llm_primary_provider", "llm_backup_provider"])

    key_obj = OrganizationLLMKey.objects.create(
        organization=org,
        provider="openai",
        api_key="placeholder",
        is_active=True,
    )
    key_obj.set_api_key("org-openai-key")
    key_obj.save(update_fields=["api_key"])

    client = get_llm_client_for_project(sample_project)
    assert isinstance(client, OpenAILLMClient)
    assert client._api_key == "org-openai-key"


@requires_postgres
@pytest.mark.django_db
def test_platform_chain_returns_fallback_client(sample_project, settings):
    org = sample_project.organization
    org.use_private_llm_credentials = False
    org.allow_platform_fallback = True
    org.save(update_fields=["use_private_llm_credentials", "allow_platform_fallback"])

    sample_project.llm_primary_provider = "openai"
    sample_project.llm_backup_provider = "gemini"
    sample_project.save(update_fields=["llm_primary_provider", "llm_backup_provider"])

    settings.OPENAI_API_KEY = "platform-openai"
    settings.GEMINI_API_KEY = "platform-gemini"
    settings.LLM_PRIMARY_PROVIDER = "openai"
    settings.LLM_BACKUP_PROVIDER = "gemini"

    client = get_llm_client_for_project(sample_project)
    assert isinstance(client, FallbackLLMClient)
