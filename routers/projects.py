import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Query, HTTPException

from services.azure_devops import AzureDevOpsService
from schemas.project import ProjectsListResponse
from schemas.backlog import ErrorResponse
from config import settings
from utils.helpers import get_env_or_param

logger = logging.getLogger("api.projects")

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get(
    "",
    response_model=ProjectsListResponse,
    responses={500: {"model": ErrorResponse, "description": "Erro interno do servidor"}}
)
async def list_projects(
    organization: Annotated[Optional[str], Query(
        description="Nome da organizacao no Azure DevOps (usa padrao do .env se nao informado)"
    )] = None,
    pat: Annotated[Optional[str], Query(
        description="Personal Access Token (usa padrao do .env se nao informado)"
    )] = None,
    top: Annotated[int, Query(
        ge=1,
        le=500,
        description="Numero maximo de projetos por pagina (1-500)"
    )] = 100,
    skip: Annotated[int, Query(
        ge=0,
        description="Numero de projetos a pular para paginacao"
    )] = 0,
    continuation_token: Annotated[Optional[str], Query(
        description="Token de continuacao para buscar proxima pagina"
    )] = None
):
    try:
        org = get_env_or_param(
            organization,
            settings.default_organization or "",
            "organization"
        )
        
        token = get_env_or_param(
            pat,
            settings.azure_devops_pat or "",
            "Personal Access Token"
        )

        logger.info(
            "Projects request | org=%s top=%s skip=%s continuation_token=%s",
            org,
            top,
            skip,
            bool(continuation_token)
        )

        service = AzureDevOpsService(
            organization=org,
            project_name="",
            pat=token
        )

        response = await service.get_projects(
            top=top,
            skip=skip,
            continuation_token=continuation_token
        )

        logger.info(
            "Projects response | org=%s count=%s has_more=%s continuation_token=%s",
            org,
            response.count,
            response.has_more,
            bool(response.continuation_token)
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar projetos: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
