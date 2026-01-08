import os
from unittest.mock import patch, AsyncMock

import aiohttp
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from config import Settings
# Importações do código principal
from main import app
from schemas.backlog import (
    WorkItemRequest,
    BacklogResponse,
    WorkItemFilters,
    WorkItemResponse
)
from services.azure_devops import AzureDevOpsService
from utils.helpers import get_env_or_param, format_date, get_first_and_last_day_of_month, generate_work_item_url, \
    create_auth_headers

# Configuração do cliente de teste
client = TestClient(app)


# Fixtures e dados de teste
@pytest.fixture
def mock_settings():
    """Fixture para configurações de teste"""
    return Settings()


@pytest.fixture
def sample_work_item_data():
    """Fixture com dados de exemplo de work item"""
    return {
        "id": 12345,
        "fields": {
            "System.Id": 12345,
            "System.Title": "Test Work Item",
            "System.State": "Active",
            "System.WorkItemType": "Task",
            "System.Tags": "test;automation",
            "System.CreatedBy": {"displayName": "John Doe"},
            "System.AssignedTo": {"displayName": "Jane Smith"},
            "System.AreaPath": "MyProject\\Area1",
            "System.TeamProject": "TestProject",
            "System.IterationPath": "MyProject\\Sprint 1",
            "Microsoft.VSTS.Scheduling.CompletedWork": 8.0,
            "Microsoft.VSTS.Scheduling.OriginalEstimate": 16.0,
            "Microsoft.VSTS.Scheduling.StartDate": "2024-01-15T09:00:00.000Z",
            "Microsoft.VSTS.Scheduling.FinishDate": "2024-01-20T17:00:00.000Z",
            "System.CreatedDate": "2024-01-10T10:30:00.000Z",
            "System.ChangedDate": "2024-01-18T14:45:00.000Z",
            "Microsoft.VSTS.Common.ClosedDate": None
        },
        "relations": [
            {
                "attributes": {"name": "Parent"},
                "url": "https://dev.azure.com/org/project/_apis/wit/workItems/12344"
            }
        ]
    }


@pytest.fixture
def sample_work_item_filters():
    """Fixture com filtros de exemplo"""
    return WorkItemFilters(
        work_item_types=["Task", "Bug"],
        states=["Active", "New"],
        area_paths=["MyProject\\Area1"],
        iteration_paths=["MyProject\\Sprint 1"],
        assigned_to=["John Doe"],
        tags="test"
    )


@pytest.fixture
def azure_service():
    """Fixture do serviço Azure DevOps"""
    return AzureDevOpsService(
        organization="test-org",
        project_name="test-project",
        pat="test-pat"
    )


# ================================
# TESTES DE UNIDADE - UTILITÁRIOS
# ================================

class TestUtilityFunctions:
    """Testes para funções utilitárias"""

    def test_get_env_or_param_with_param(self):
        """Testa get_env_or_param quando parâmetro é fornecido"""
        result = get_env_or_param("param_value", "env_value", "test_param")
        assert result == "param_value"

    def test_get_env_or_param_with_env(self):
        """Testa get_env_or_param quando apenas env está definido"""
        result = get_env_or_param(None, "env_value", "test_param")
        assert result == "env_value"

    def test_get_env_or_param_missing_both(self):
        """Testa get_env_or_param quando ambos estão ausentes"""
        with pytest.raises(HTTPException) as exc_info:
            get_env_or_param(None, "", "test_param")
        assert exc_info.value.status_code == 400
        assert "test_param deve ser fornecido" in str(exc_info.value.detail)

    def test_format_date_valid(self):
        """Testa formatação de data válida"""
        iso_date = "2024-01-15T10:30:00.000Z"
        result = format_date(iso_date)
        assert result == "15/01/2024"

    def test_format_date_invalid(self):
        """Testa formatação de data inválida"""
        result = format_date("invalid-date")
        assert result is None

    def test_format_date_empty(self):
        """Testa formatação de data vazia"""
        result = format_date("")
        assert result is None

    def test_get_first_and_last_day_of_month(self):
        """Testa obtenção do primeiro e último dia do mês"""
        start, end = get_first_and_last_day_of_month(2024, 2)
        assert start == "2024-02-01"
        assert end == "2024-02-29"  # Ano bissexto

    def test_generate_work_item_url(self):
        """Testa geração de URL do work item"""
        url = generate_work_item_url("12345", "test-org", "test-project")
        expected = "https://dev.azure.com/test-org/test-project/_workitems/edit/12345"
        assert url == expected

    def test_create_auth_headers(self):
        """Testa criação de headers de autenticação"""
        headers = create_auth_headers("test-pat")
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")
        assert headers["Content-Type"] == "application/json"


# ================================
# TESTES DE UNIDADE - SETTINGS
# ================================

class TestSettings:
    """Testes para a classe Settings"""

    @patch.dict(os.environ, {
        "AZURE_DEVOPS_PAT": "test-pat",
        "AZURE_DEVOPS_ORGANIZATION": "test-org",
        "AZURE_DEVOPS_PROJECT": "test-project"
    })
    def test_settings_initialization_with_env(self):
        """Testa inicialização das configurações com variáveis de ambiente"""
        settings = Settings()
        assert settings.azure_devops_pat == "test-pat"
        assert settings.default_organization == "test-org"
        assert settings.default_project == "test-project"

    @patch.dict(os.environ, {"AZURE_DEVOPS_PAT": "test-pat"}, clear=True)
    def test_validate_required_env_vars_success(self):
        """Testa validação bem-sucedida das variáveis obrigatórias"""
        settings = Settings()
        # Não deve lançar exceção
        settings.validate_required_env_vars()

    @patch.dict(os.environ, {}, clear=True)
    def test_validate_required_env_vars_missing(self):
        """Testa validação com variáveis obrigatórias ausentes"""
        settings = Settings()
        with pytest.raises(ValueError) as exc_info:
            settings.validate_required_env_vars()
        assert "AZURE_DEVOPS_PAT" in str(exc_info.value)


# ================================
# TESTES DE UNIDADE - AZURE DEVOPS SERVICE
# ================================

class TestAzureDevOpsService:
    """Testes para a classe AzureDevOpsService"""

    def test_service_initialization(self, azure_service):
        """Testa inicialização do serviço"""
        assert azure_service.organization == "test-org"
        assert azure_service.project_name == "test-project"
        assert azure_service.pat == "test-pat"
        assert "Authorization" in azure_service.headers

    def test_summarize_filters_empty(self, azure_service):
        result = azure_service._summarize_filters(None)
        assert result == "none"

    def test_summarize_filters_with_data(self, azure_service, sample_work_item_filters):
        result = azure_service._summarize_filters(sample_work_item_filters)
        assert "types=2" in result
        assert "states=2" in result

    def test_categorize_work_items_parents(self, azure_service, sample_work_item_data):
        sample_work_item_data["fields"]["System.WorkItemType"] = "User Story"
        parents, children = azure_service._categorize_work_items([sample_work_item_data])
        assert len(parents) == 1
        assert len(children) == 0

    def test_categorize_work_items_children(self, azure_service, sample_work_item_data):
        sample_work_item_data["fields"]["System.WorkItemType"] = "Task"
        parents, children = azure_service._categorize_work_items([sample_work_item_data])
        assert len(parents) == 0
        assert len(children) == 1

    def test_categorize_work_items_empty(self, azure_service):
        parents, children = azure_service._categorize_work_items([])
        assert len(parents) == 0
        assert len(children) == 0

    @pytest.mark.asyncio
    async def test_get_backlog_data_success(self, azure_service, sample_work_item_data):
        query_ids = [12345]
        sample_work_item_data["fields"]["System.WorkItemType"] = "Task"

        with patch.object(azure_service, '_query_work_items', return_value=query_ids):
            with patch.object(azure_service, '_get_work_items_details', return_value=[sample_work_item_data]):
                result = await azure_service.get_backlog_data("2024-01-01", "2024-01-31")

                assert isinstance(result, BacklogResponse)
                assert result.total_items == 1
                assert len(result.children) == 1

    @pytest.mark.asyncio
    async def test_get_backlog_data_no_items(self, azure_service):
        with patch.object(azure_service, '_query_work_items', return_value=[]):
            result = await azure_service.get_backlog_data("2024-01-01", "2024-01-31")

            assert isinstance(result, BacklogResponse)
            assert result.total_items == 0
            assert len(result.parents) == 0
            assert len(result.children) == 0


# ================================
# TESTES DE INTEGRAÇÃO - ENDPOINTS
# ================================

class TestEndpoints:
    """Testes de integração para os endpoints da API"""

    def test_root_endpoint(self):
        """Testa endpoint raiz"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Azure DevOps Backlog API"
        assert data["status"] == "online"

    def test_health_endpoint(self):
        """Testa endpoint de health check"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"

    @patch.dict(os.environ, {"AZURE_DEVOPS_PAT": "test-pat"})
    def test_post_backlog_endpoint_success(self):
        """Testa endpoint POST /backlog com sucesso"""
        request_data = {
            "organization": "test-org",
            "project_name": "test-project",
            "pat": "test-pat",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        }

        mock_response = BacklogResponse(
            total_items=1,
            parents=[],
            children=[],
            metadata={"test": "data"}
        )

        with patch('routers.backlog.AzureDevOpsService.get_backlog_data', return_value=mock_response):
            response = client.post("/backlog", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["total_items"] == 1

    @patch.dict(os.environ, {"AZURE_DEVOPS_PAT": "test-pat"})
    def test_post_backlog_endpoint_with_year_month(self):
        """Testa endpoint POST /backlog com ano e mês"""
        request_data = {
            "project_name": "meu-projeto",
            "organization": "minha-org",
            "pat": "fake-pat",
            "year": 2024,
            "month": 1
        }

        mock_response = BacklogResponse(
            total_items=0,
            parents=[],
            children=[],
            metadata={"test": "data"}
        )

        with patch('routers.backlog.AzureDevOpsService.get_backlog_data', return_value=mock_response):
            response = client.post("/backlog", json=request_data)

            assert response.status_code == 200

    def test_post_backlog_endpoint_invalid_date(self):
        """Testa endpoint POST /backlog com data inválida"""
        request_data = {
            "organization": "test-org",
            "project_name": "test-project",
            "pat": "test-pat",
            "start_date": "invalid-date",
            "end_date": "2024-01-31"
        }

        response = client.post("/backlog", json=request_data)

        assert response.status_code == 400
        assert "Formato de data inválido" in response.json()["detail"]

    @patch.dict(os.environ, {"AZURE_DEVOPS_PAT": "test-pat", "AZURE_DEVOPS_ORGANIZATION": "test", "AZURE_DEVOPS_PROJECT": "test-project"})
    def test_get_backlog_endpoint_success(self):
        """Testa endpoint GET /backlog com sucesso"""
        mock_response = BacklogResponse(
            total_items=1,
            parents=[],
            children=[],
            metadata={"test": "data"}
        )

        with patch('routers.backlog.AzureDevOpsService.get_backlog_data', return_value=mock_response):
            response = client.get("/backlog?organization=test&pat=test-pat&project_name=test-project")

            assert response.status_code == 200
            data = response.json()
            assert data["total_items"] == 1

    @patch.dict(os.environ, {"AZURE_DEVOPS_PAT": "test-pat"})
    def test_get_backlog_endpoint_with_filters(self):
        """Testa endpoint GET /backlog com filtros"""
        mock_response = BacklogResponse(
            total_items=0,
            parents=[],
            children=[],
            metadata={"test": "data"}
        )

        with patch('routers.backlog.AzureDevOpsService.get_backlog_data', return_value=mock_response):
            response = client.get(
                "/backlog?organization=test&pat=test-pat&project_name=test-project&work_item_types=Task,Bug&states=Active,New"
            )

            assert response.status_code == 200

    def test_get_backlog_endpoint_missing_project(self):
        """Testa endpoint GET /backlog sem nome do projeto"""
        response = client.get("/backlog")

        assert response.status_code == 422  # Validation error


# ================================
# TESTES DE MODELOS PYDANTIC
# ================================

class TestPydanticModels:
    """Testes para os modelos Pydantic"""

    def test_work_item_filters_creation(self):
        """Testa criação de WorkItemFilters"""
        filters = WorkItemFilters(
            work_item_types=["Task", "Bug"],
            states=["Active"],
            area_paths=["Area1"],
            iteration_paths=["Sprint1"],
            assigned_to=["User1"],
            tags="test"
        )

        assert filters.work_item_types == ["Task", "Bug"]
        assert filters.states == ["Active"]
        assert filters.tags == "test"

    def test_work_item_request_creation(self):
        """Testa criação de WorkItemRequest"""
        request = WorkItemRequest(
            organization="test-org",
            project_name="test-project",
            pat="test-pat",
            start_date="2024-01-01",
            end_date="2024-01-31"
        )

        assert request.organization == "test-org"
        assert request.project_name == "test-project"
        assert request.start_date == "2024-01-01"

    def test_work_item_response_creation(self):
        """Testa criação de WorkItemResponse"""
        response = WorkItemResponse(
            id=12345,
            title="Test Item",
            state="Active",
            work_item_type="Task",
            tags="test",
            created_by="John Doe",
            assigned_to="Jane Smith",
            area_path="Area1",
            team_project="Project1",
            iteration_path="Sprint1",
            completed_work=8.0,
            original_estimate=16.0,
            start_date="15/01/2024",
            finish_date="20/01/2024",
            created_date="10/01/2024",
            changed_date="18/01/2024",
            closed_date=None,
            parent_id=12344,
            parent_link="https://example.com"
        )

        assert response.id == 12345
        assert response.title == "Test Item"
        assert response.completed_work == 8.0

    def test_backlog_response_creation(self):
        """Testa criação de BacklogResponse"""
        work_item = WorkItemResponse(
            id=1, title="Test", state="Active", work_item_type="Task",
            tags=None, created_by=None, assigned_to=None, area_path=None,
            team_project=None, iteration_path=None, completed_work=None,
            original_estimate=None, start_date=None, finish_date=None,
            created_date=None, changed_date=None, closed_date=None,
            parent_id=None, parent_link=None
        )

        response = BacklogResponse(
            total_items=1,
            parents=[work_item],
            children=[],
            metadata={"test": "data"}
        )

        assert response.total_items == 1
        assert len(response.parents) == 1
        assert len(response.children) == 0


# ================================
# TESTES DE ERRO E EDGE CASES
# ================================

class TestErrorHandling:

    @pytest.mark.asyncio
    async def test_azure_service_query_error(self, azure_service):
        with patch.object(azure_service, '_query_work_items', side_effect=HTTPException(status_code=400, detail="Query error")):
            with pytest.raises(HTTPException) as exc_info:
                await azure_service.get_backlog_data("2024-01-01", "2024-01-31")

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_azure_service_unexpected_error(self, azure_service):
        with patch.object(azure_service, '_query_work_items', side_effect=Exception("Unexpected error")):
            with pytest.raises(Exception):
                await azure_service.get_backlog_data("2024-01-01", "2024-01-31")

    def test_endpoint_internal_server_error(self):
        """Testa erro interno do servidor no endpoint"""
        request_data = {
            "organization": "test-org",
            "project_name": "test-project",
            "pat": "test-pat",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        }

        with patch('routers.backlog.AzureDevOpsService.get_backlog_data', side_effect=Exception("Internal error")):
            response = client.post("/backlog", json=request_data)

            assert response.status_code == 500
            assert "Erro interno do servidor" in response.json()["detail"]


# ================================
# TESTES DE PERFORMANCE
# ================================

class TestPerformance:

    @pytest.mark.asyncio
    async def test_concurrent_work_item_fetching(self, azure_service, sample_work_item_data):
        query_ids = list(range(1, 11))
        work_items = []
        for i in query_ids:
            item = {
                "id": i,
                "fields": {
                    "System.Id": i,
                    "System.Title": f"Test Item {i}",
                    "System.State": "Active",
                    "System.WorkItemType": "Task",
                    "System.Tags": "test",
                    "System.CreatedBy": {"displayName": "John"},
                    "System.AssignedTo": {"displayName": "Jane"},
                    "System.AreaPath": "Area1",
                    "System.TeamProject": "TestProject",
                    "System.IterationPath": "Sprint1"
                }
            }
            work_items.append(item)

        with patch.object(azure_service, '_query_work_items', return_value=query_ids):
            with patch.object(azure_service, '_get_work_items_details', return_value=work_items):
                import time
                start_time = time.time()

                result = await azure_service.get_backlog_data("2024-01-01", "2024-01-31")

                end_time = time.time()
                execution_time = end_time - start_time

                assert execution_time < 5.0
                assert result.total_items == 10


# ================================
# CONFIGURAÇÃO DE TESTES
# ================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Configuração global para os testes"""
    # Configura variáveis de ambiente para testes
    os.environ["AZURE_DEVOPS_PAT"] = "test-pat-for-testing"
    os.environ["AZURE_DEVOPS_ORGANIZATION"] = "test-org"
    os.environ["AZURE_DEVOPS_PROJECT"] = "test-project"
    yield
    # Limpa após os testes
    for key in ["AZURE_DEVOPS_PAT", "AZURE_DEVOPS_ORGANIZATION", "AZURE_DEVOPS_PROJECT"]:
        if key in os.environ:
            del os.environ[key]


if __name__ == "__main__":
    # Executa os testes
    pytest.main([
        "-v",
        "--tb=short",
        "--cov=main",
        "--cov-report=term-missing",
        "--cov-report=html",
        __file__
    ])
