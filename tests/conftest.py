# tests/conftest.py

from fastapi import HTTPException

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app  # Importação atualizada
from schemas.backlog import BacklogResponse, WorkItemResponse  # Importação do novo módulo


@pytest.fixture(scope="module")
def test_client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock de variáveis de ambiente essenciais"""
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "dummy_pat")
    monkeypatch.setenv("AZURE_DEVOPS_ORGANIZATION", "default_org")
    monkeypatch.setenv("AZURE_DEVOPS_PROJECT", "default_project")


@pytest.fixture
def mock_azure_service():
    """Mock do AzureDevOpsService com métodos assíncronos e dados válidos"""
    # Atualização do caminho do mock
    with patch('routers.backlog.AzureDevOpsService', autospec=True) as mock:
        instance = mock.return_value
        # Configura o retorno com uma estrutura válida
        instance.get_backlog_data.return_value = BacklogResponse(
            total_items=0,
            parents=[],
            children=[],
            metadata={
                "start_date": "2023-11-01",
                "end_date": "2023-11-30",
                "organization": "test_org",
                "project": "test_project",
                "parents_count": 0,
                "children_count": 0,
                "applied_filters": {}
            }
        )
        yield instance


# tests/conftest.py

from datetime import datetime

@pytest.fixture
def mock_azure_service_two_items():
    """Mock com dois Work Items completos conforme schema"""
    with patch('routers.backlog.AzureDevOpsService', autospec=True) as mock:
        instance = mock.return_value
        instance.get_backlog_data.return_value = BacklogResponse(
            total_items=2,
            parents=[
                WorkItemResponse(
                    id=1,
                    title="Item Pai 1",
                    state="Active",
                    work_item_type="User Story",
                    tags="frontend",
                    created_by="Usuário A",
                    assigned_to="Dev A",
                    area_path="Área/Projeto",
                    team_project="meu-projeto",
                    iteration_path="Sprint 1",
                    completed_work=5.0,
                    original_estimate=8.0,
                    start_date="2024-05-01",
                    finish_date="2024-05-15",
                    created_date="2024-05-01",
                    changed_date="2024-05-10",
                    closed_date=None,
                    parent_id=None,
                    parent_link=None
                ),
                WorkItemResponse(
                    id=2,
                    title="Item Pai 2",
                    state="New",
                    work_item_type="Bug",
                    tags="backend",
                    created_by="Usuário B",
                    assigned_to="Dev B",
                    area_path="Área/Projeto",
                    team_project="meu-projeto",
                    iteration_path="Sprint 2",
                    completed_work=0.0,
                    original_estimate=3.0,
                    start_date="2024-05-05",
                    finish_date=None,
                    created_date="2024-05-05",
                    changed_date="2024-05-08",
                    closed_date=None,
                    parent_id=None,
                    parent_link=None
                )
            ],
            children=[],
            metadata={
                "start_date": "2024-05-01",
                "end_date": "2024-05-31",
                "organization": "minha-org",
                "project": "meu-projeto",
                "parents_count": 2,
                "children_count": 0,
                "applied_filters": {}
            }
        )
        yield instance


@pytest.fixture
def mock_azure_service_with_filters():
    """Mock que aceita filtros como argumento"""
    with patch("routers.backlog.AzureDevOpsService", autospec=True) as mock:
        instance = mock.return_value

        # Retorno padrão, o foco é verificar os filtros passados
        instance.get_backlog_data.return_value = BacklogResponse(
            total_items=1,
            parents=[],
            children=[],
            metadata={"applied_filters": {
                "work_item_types": ["Bug", "User Story"],
                "states": ["New", "Active"],
                "tags": "urgent"
            }}
        )
        yield instance


@pytest.fixture
def mock_azure_service_with_error():
    """Mock que simula erro HTTP vindo do Azure"""
    with patch('routers.backlog.AzureDevOpsService', autospec=True) as mock:
        instance = mock.return_value
        instance.get_backlog_data.side_effect = HTTPException(
            status_code=404,
            detail="Projeto não encontrado no Azure DevOps"
        )
        yield instance