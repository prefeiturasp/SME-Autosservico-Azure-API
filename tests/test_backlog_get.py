# tests/test_backlog_get.py
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi import status

from schemas.backlog import BacklogResponse, WorkItemResponse


# Caso de sucesso - Parâmetros mínimos
@pytest.mark.asyncio
async def test_get_backlog_success(test_client, mock_azure_service):
    # Configura dados de retorno válidos
    mock_response = BacklogResponse(
        total_items=2,
        parents=[
            WorkItemResponse(
                id=123,
                title="Parent Item",
                state="Active",
                work_item_type="Feature",
                tags="tag1;tag2",
                created_by="user@example.com",
                assigned_to="user@example.com",
                area_path="Area1",
                team_project="test_project",
                iteration_path="Iteration1",
                completed_work=5.0,
                original_estimate=10.0,
                start_date="2023-11-01",
                finish_date="2023-11-30",
                created_date="2023-11-01",
                changed_date="2023-11-05",
                closed_date=None,
                parent_id=None,
                parent_link="https://dev.azure.com/test_org/test_project/_workitems/edit/123"
            )
        ],
        children=[
            WorkItemResponse(
                id=456,
                title="Child Item",
                state="New",
                work_item_type="Task",
                tags="tag1",
                created_by="user@example.com",
                assigned_to="user@example.com",
                area_path="Area1",
                team_project="test_project",
                iteration_path="Iteration1",
                completed_work=2.0,
                original_estimate=5.0,
                start_date="2023-11-02",
                finish_date="2023-11-15",
                created_date="2023-11-02",
                changed_date="2023-11-03",
                closed_date=None,
                parent_id=123,
                parent_link="https://dev.azure.com/test_org/test_project/_workitems/edit/123"
            )
        ],
        metadata={
            "start_date": "2023-11-01",
            "end_date": "2023-11-30",
            "organization": "test_org",
            "project": "test_project",
            "parents_count": 1,
            "children_count": 1,
            "applied_filters": {}
        }
    )
    mock_azure_service.get_backlog_data.return_value = mock_response

    response = test_client.get(
        "/backlog",
        params={
            "project_name": "test_project",
            "organization": "minha-org",
            "pat": "dummy_pat",  # Simula o PAT
            "year": 2023,
            "month": 11
        }
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()

    # Verifica estrutura básica
    assert "total_items" in response_data
    assert "parents" in response_data
    assert "children" in response_data
    assert "metadata" in response_data

    # Verifica se o serviço foi chamado corretamente
    mock_azure_service.get_backlog_data.assert_awaited_once()


# Caso com filtros via query params
@pytest.mark.asyncio
async def test_get_backlog_with_query_filters(test_client, mock_azure_service):
    test_client.get(
        "/backlog",
        params={
            "project_name": "test_project",
            "organization": "minha-org",
            "pat": "dummy_pat",  # Simula o PAT
            "year": 2023,
            "month": 11,
            "work_item_types": "Bug,Task",
            "states": "New,Active",
            "tags": "high_priority"
        }
    )

    called_args = mock_azure_service.get_backlog_data.call_args[0]
    filters = called_args[2]

    assert filters.work_item_types == ["Bug", "Task"]
    assert filters.states == ["New", "Active"]
    assert filters.tags == "high_priority"


# Caso de erro - Projeto ausente
@pytest.mark.asyncio
async def test_get_backlog_missing_project(test_client):
    response = test_client.get(
        "/backlog",
        params={
            "year": 2023,
            "month": 11
        }
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# Teste de conversão de parâmetros
@pytest.mark.asyncio
async def test_get_backlog_parameter_conversion(test_client, mock_azure_service):
    response = test_client.get(
        "/backlog",
        params={
            "project_name": "test_project",
            "organization": "minha-org",
            "pat": "dummy_pat",  # Simula o PAT
            "year": "2023",  # String deve ser convertida
            "month": "11"  # String deve ser convertida
        }
    )
    assert response.status_code == status.HTTP_200_OK


# Teste de datas opcionais (sem filtro de data quando não especificado)
def test_get_backlog_default_dates(test_client, mock_azure_service):
    """Testa se nenhum filtro de data é aplicado quando nenhuma data é fornecida"""
    # Configura o retorno do mock
    mock_azure_service.get_backlog_data.return_value = BacklogResponse(
        total_items=0,
        parents=[],
        children=[],
        metadata={
            "start_date": "none",
            "end_date": "none",
            "organization": "test_org",
            "project": "test_project",
            "parents_count": 0,
            "children_count": 0,
            "applied_filters": {}
        }
    )

    response = test_client.get(
        "/backlog",
        params={
            "project_name": "test_project",
            "organization": "minha-org",
            "pat": "dummy_pat",  # Simula o PAT
        }
    )

    assert response.status_code == status.HTTP_200_OK

    # Verifica os argumentos usados na chamada do serviço
    # Quando nenhuma data é fornecida, start_date e end_date devem ser None
    called_args = mock_azure_service.get_backlog_data.call_args[0]
    assert called_args[0] is None  # start_date
    assert called_args[1] is None  # end_date
