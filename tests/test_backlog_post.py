import pytest
from fastapi import status
from fastapi.testclient import TestClient
from main import app
from aioresponses import aioresponses
from services.azure_devops import WorkItemFilters

client = TestClient(app)

@pytest.fixture
def backlog_request_data():
    return {
        "project_name": "meu-projeto",
        "organization": "minha-org",
        "pat": "fake-pat",
        "year": 2024,
        "month": 5
    }

def test_backlog_post_with_valid_dates(backlog_request_data):
    with aioresponses() as mocked:

        # URL da WIQL com query param
        wiql_url = "https://dev.azure.com/minha-org/meu-projeto/_apis/wit/wiql?api-version=6.0"
        mocked.post(wiql_url, status=200, payload={
            "workItems": [{"id": 123, "url": "https://fake-url.com/wi/123"}]
        })

        # URL dos detalhes do WorkItem com $expand
        mocked.get("https://fake-url.com/wi/123?$expand=all", status=200, payload={
            "id": 123,
            "fields": {
                "System.Id": 123,
                "System.Title": "Título Teste",
                "System.TeamProject": "meu-projeto",
                "System.State": "Active",
                "System.WorkItemType": "Bug",
                "System.Tags": "bug",
                "System.CreatedBy": {"displayName": "Criador"},
                "System.AssignedTo": {"displayName": "Dev"},
                "System.AreaPath": "Area/Teste",
                "System.IterationPath": "Iteracao 1",
                "System.CreatedDate": "2024-05-10T00:00:00Z",
                "System.ChangedDate": "2024-05-11T00:00:00Z",
                "Microsoft.VSTS.Scheduling.CompletedWork": 5.0,
                "Microsoft.VSTS.Scheduling.OriginalEstimate": 8.0,
            }
        })

        response = client.post("/backlog", json=backlog_request_data)

        assert response.status_code == 200
        assert response.json()["total_items"] == 1


def test_backlog_post_with_mocked_service(
    backlog_request_data,
    mock_azure_service  # ⚠️ é passado automaticamente pelo pytest, vem do conftest.py
):
    response = client.post("/backlog", json=backlog_request_data)

    # ✅ Verifica se a chamada foi bem-sucedida
    assert response.status_code == 200

    # ✅ Verifica se o retorno mockado do AzureDevOpsService está presente
    json_data = response.json()
    assert json_data["total_items"] == 0
    assert json_data["metadata"]["organization"] == "test_org"
    assert json_data["metadata"]["project"] == "test_project"

    # ✅ Garante que o método do serviço foi chamado corretamente
    mock_azure_service.get_backlog_data.assert_called_once()


def test_backlog_post_with_two_items(
    backlog_request_data,
    mock_azure_service_two_items
):
    response = client.post("/backlog", json=backlog_request_data)

    assert response.status_code == 200
    json_data = response.json()

    assert json_data["total_items"] == 2
    assert len(json_data["parents"]) == 2
    assert json_data["metadata"]["parents_count"] == 2

    mock_azure_service_two_items.get_backlog_data.assert_called_once()


def test_backlog_post_with_azure_error(
    backlog_request_data,
    mock_azure_service_with_error
):
    response = client.post("/backlog", json=backlog_request_data)

    assert response.status_code == 404
    assert response.json() == {"detail": "Projeto não encontrado no Azure DevOps"}

    mock_azure_service_with_error.get_backlog_data.assert_called_once()


def test_backlog_post_missing_pat(monkeypatch):
    # Simula que o PAT está no .env (como já está no settings)
    monkeypatch.setenv("AZURE_DEVOPS_PAT", "pat-falso")

    request_data = {
        "project_name": "meu-projeto",
        "organization": "minha-org",
        "year": 2024,
        "month": 5
    }

    with aioresponses() as mocked:
        # Captura a tentativa de consulta com o PAT "pat-falso" mockando erro
        mocked.post("https://dev.azure.com/minha-org/meu-projeto/_apis/wit/wiql?api-version=6.0",
                    status=401,  # ou 403
                    payload={"error": "PAT inválido"}
        )

        response = client.post("/backlog", json=request_data)

        assert response.status_code == 400
        assert response.text == '{"detail":"Personal Access Token deve ser fornecido no request ou definido no .env"}'


# Caso de sucesso - Parâmetros mínimos
@pytest.mark.asyncio
async def test_post_backlog_success(test_client, mock_azure_service_two_items):
    # Executar requisição
    payload = {
        "project_name": "meu-projeto",
        "organization": "minha-org",
        "pat": "fake-pat",
        "year": 2023,
        "month": 11
    }
    response = test_client.post("/backlog", json=payload)

    # Verificações
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["total_items"] == 2
    mock_azure_service_two_items.get_backlog_data.assert_awaited_once()



# Caso com filtros complexos
@pytest.mark.asyncio
async def test_post_backlog_with_filters(test_client, mock_azure_service_with_filters):
    payload = {
        "project_name": "meu-projeto",
        "organization": "minha-org",
        "pat": "fake-pat",
        "year": 2023,
        "month": 11,
        "filters": {
            "work_item_types": ["Bug", "User Story"],
            "states": ["New", "Active"],
            "tags": "urgent"
        }
    }
    test_client.post("/backlog", json=payload)

    # Verificar estrutura dos filtros
    called_args = mock_azure_service_with_filters.get_backlog_data.call_args[0]
    filters = called_args[2]

    assert isinstance(filters, WorkItemFilters)
    assert filters.work_item_types == ["Bug", "User Story"]
    assert filters.states == ["New", "Active"]
    assert filters.tags == "urgent"


# Caso de erro - Datas inválidas
@pytest.mark.asyncio
async def test_post_backlog_invalid_dates(test_client):
    payload = {
        "organization": "SME-Spassu",
        "pat": "SME-Spassu",
        "project_name": "test_project",
        "start_date": "2023-13-01",  # Mês inválido
        "end_date": "2023-12-01"
    }
    response = test_client.post("/backlog", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Formato de data inválido" in response.json()["detail"]