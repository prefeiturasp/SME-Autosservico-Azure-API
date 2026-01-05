import logging

from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime
from services.azure_devops import AzureDevOpsService
from schemas.backlog import (
    WorkItemRequest,
    BacklogResponse,
    WorkItemFilters
)
from config import settings
from utils.helpers import get_env_or_param, get_first_and_last_day_of_month

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@router.post("/backlog", response_model=BacklogResponse, tags=["Backlog"])
async def get_backlog(request: WorkItemRequest):
    """
    Extrai dados do backlog do Azure DevOps

    Pode ser usado de duas formas:
    1. Com start_date e end_date específicas
    2. Com year e month para buscar dados do mês completo

    O PAT pode ser fornecido no request ou estar configurado no .env
    """
    try:
        # Resolve valores a partir do .env ou parâmetros
        organization = get_env_or_param(
            request.organization,
            settings.default_organization,
            "organization"
        )

        pat = get_env_or_param(
            request.pat,
            settings.azure_devops_pat,
            "Personal Access Token"
        )

        # Determina as datas
        if request.start_date and request.end_date:
            start_date = request.start_date
            end_date = request.end_date
        elif request.year and request.month:
            start_date, end_date = get_first_and_last_day_of_month(request.year, request.month)
        else:
            # Usa mês atual como padrão
            current_date = datetime.now()
            start_date, end_date = get_first_and_last_day_of_month(
                current_date.year,
                current_date.month
            )

        # Validação de datas
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Formato de data inválido. Use YYYY-MM-DD"
            )

        # Cria o serviço e busca os dados
        service = AzureDevOpsService(
            organization=organization,
            project_name=request.project_name,
            pat=pat
        )

        return await service.get_backlog_data(start_date, end_date, request.filters)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")


@router.get("/backlog", response_model=BacklogResponse, tags=["Backlog"])
async def get_backlog_query_params(
        project_name: str = Query(..., description="Nome do projeto"),
        organization: Optional[str] = Query(None,
                                            description="Nome da organização no Azure DevOps (usa padrão do .env se não informado)"),
        pat: Optional[str] = Query(None, description="Personal Access Token (usa padrão do .env se não informado)"),
        start_date: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
        end_date: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
        year: Optional[int] = Query(None, description="Ano para busca por mês"),
        month: Optional[int] = Query(None, description="Mês (1-12) para busca por mês"),
        work_item_types: Optional[str] = Query(None,
                                               description="Tipos de work items separados por vírgula (Bug,Task,User Story)"),
        states: Optional[str] = Query(None, description="Estados separados por vírgula (New,Active,Resolved)"),
        area_paths: Optional[str] = Query(None, description="Caminhos de área separados por vírgula"),
        iteration_paths: Optional[str] = Query(None, description="Caminhos de iteração separados por vírgula"),
        assigned_to: Optional[str] = Query(None, description="Usuários atribuídos separados por vírgula"),
        tags: Optional[str] = Query(None, description="Tags específicas")
):
    """
    Endpoint GET alternativo para extração do backlog usando query parameters
    O PAT pode ser fornecido como parâmetro ou estar configurado no .env
    """
    # Constrói filtros a partir dos query parameters
    filters = None
    if any([work_item_types, states, area_paths, iteration_paths, assigned_to, tags]):
        filters = WorkItemFilters(
            work_item_types=work_item_types.split(',') if work_item_types else None,
            states=states.split(',') if states else None,
            area_paths=area_paths.split(',') if area_paths else None,
            iteration_paths=iteration_paths.split(',') if iteration_paths else None,
            assigned_to=assigned_to.split(',') if assigned_to else None,
            tags=tags
        )

    request = WorkItemRequest(
        organization=organization,
        project_name=project_name,
        pat=pat,
        start_date=start_date,
        end_date=end_date,
        year=year,
        month=month,
        filters=filters
    )

    return await get_backlog(request)