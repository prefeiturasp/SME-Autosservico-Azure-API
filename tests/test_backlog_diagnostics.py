# tests/test_backlog_diagnostics.py
import pytest
from fastapi import status

from schemas.backlog import BacklogResponse, WorkItemResponse


def _item(item_id, title, work_item_type, state):
    return WorkItemResponse(
        id=item_id, title=title, work_item_type=work_item_type, state=state
    )


def test_diagnostics_success(test_client, mock_azure_service):
    """Conta os work items por tipo e devolve amostra dos itens."""
    mock_azure_service.get_backlog_data.return_value = BacklogResponse(
        total_items=3,
        parents=[_item(1, "Feature A", "Feature", "Active")],
        children=[
            _item(2, "Bug 1", "BugFix", "New"),
            _item(3, "Bug 2", "BugFix", "Resolved"),
        ],
        metadata={},
    )

    response = test_client.get(
        "/backlog/diagnostics",
        params={"project_name": "SME - Sustentação", "organization": "minha-org"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_items"] == 3
    assert data["work_item_type_counts"] == {"Feature": 1, "BugFix": 2}
    assert len(data["sample_items"]) == 3
    mock_azure_service.get_backlog_data.assert_awaited_once()


def test_diagnostics_handles_unknown_type(test_client, mock_azure_service):
    """Item sem work_item_type é contabilizado como 'Unknown'."""
    mock_azure_service.get_backlog_data.return_value = BacklogResponse(
        total_items=1,
        parents=[],
        children=[_item(10, "Sem tipo", None, "New")],
        metadata={},
    )

    response = test_client.get(
        "/backlog/diagnostics", params={"project_name": "proj"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["work_item_type_counts"] == {"Unknown": 1}


def test_diagnostics_missing_project(test_client):
    """project_name é obrigatório."""
    response = test_client.get("/backlog/diagnostics")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_diagnostics_handles_error(test_client, mock_azure_service):
    """Erro do serviço é convertido em 500."""
    mock_azure_service.get_backlog_data.side_effect = Exception("falha")
    response = test_client.get(
        "/backlog/diagnostics", params={"project_name": "proj"}
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
