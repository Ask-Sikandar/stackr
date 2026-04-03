import pytest

from apps.ai.consumers import _resolve_project_from_ws_payload
from tests.conftest import requires_postgres


@requires_postgres
@pytest.mark.django_db
def test_ws_project_resolution_requires_both_project_and_token():
    with pytest.raises(ValueError):
        _resolve_project_from_ws_payload(project_id=1, access_token=None)


@requires_postgres
@pytest.mark.django_db
def test_ws_project_resolution_rejects_invalid_token():
    with pytest.raises(ValueError):
        _resolve_project_from_ws_payload(project_id=1, access_token="invalid-token")
