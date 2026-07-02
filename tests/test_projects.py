# tests/test_projects.py
from unittest.mock import patch

import pytest
from fastapi import status, HTTPException

from schemas.project import ProjectsListResponse, ProjectResponse


@pytest.fixture
def mock_projects_service():
    """Mock do AzureDevOpsService usado pelo router de projects."""
    with patch("routers.projects.AzureDevOpsService", autospec=True) as mock:
        instance = mock.return_value
        instance.get_projects.return_value = ProjectsListResponse(
            count=1,
            total_count=1,
            projects=[
                ProjectResponse(
                    id="abc-123",
                    name="SME - Sustentação",
                    description="Projeto de exemplo",
                    url="https://dev.azure.com/org/_apis/projects/abc-123",
                    state="wellFormed",
                    revision=10,
                    visibility="private",
                    last_update_time="2024-05-01T00:00:00Z",
                )
            ],
            continuation_token=None,
            has_more=False,
        )
        yield instance


def test_list_projects_success(test_client, mock_projects_service):
    response = test_client.get(
        "/projects",
        params={"organization": "minha-org", "pat": "dummy_pat", "top": 50, "skip": 0},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["count"] == 1
    assert data["projects"][0]["name"] == "SME - Sustentação"
    assert data["has_more"] is False
    mock_projects_service.get_projects.assert_awaited_once()


def test_list_projects_uses_default_params(test_client, mock_projects_service):
    """Sem top/skip, usa os valores padrão (100/0)."""
    response = test_client.get("/projects", params={"pat": "dummy_pat"})

    assert response.status_code == status.HTTP_200_OK
    kwargs = mock_projects_service.get_projects.call_args.kwargs
    assert kwargs["top"] == 100
    assert kwargs["skip"] == 0


def test_list_projects_invalid_top(test_client, mock_projects_service):
    """top fora do intervalo permitido (1-500) deve retornar 422."""
    response = test_client.get("/projects", params={"top": 999})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_list_projects_propagates_http_exception(test_client, mock_projects_service):
    """HTTPException vinda do serviço é repassada com o mesmo status."""
    mock_projects_service.get_projects.side_effect = HTTPException(
        status_code=404, detail="Organização não encontrada"
    )
    response = test_client.get("/projects", params={"pat": "dummy_pat"})
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_list_projects_handles_unexpected_error(test_client, mock_projects_service):
    """Erro inesperado é convertido em 500."""
    mock_projects_service.get_projects.side_effect = Exception("falha inesperada")
    response = test_client.get("/projects", params={"pat": "dummy_pat"})
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
