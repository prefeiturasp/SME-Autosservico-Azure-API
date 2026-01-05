import logging
from typing import Optional

from fastapi import APIRouter, Query, HTTPException

from services.azure_devops import AzureDevOpsService
from schemas.project import ProjectsListResponse
from config import settings
from utils.helpers import get_env_or_param

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=ProjectsListResponse)
async def list_projects(
    organization: Optional[str] = Query(
        None,
        description="Nome da organizacao no Azure DevOps (usa padrao do .env se nao informado)"
    ),
    pat: Optional[str] = Query(
        None,
        description="Personal Access Token (usa padrao do .env se nao informado)"
    ),
    top: int = Query(
        100,
        ge=1,
        le=500,
        description="Numero maximo de projetos por pagina (1-500)"
    ),
    skip: int = Query(
        0,
        ge=0,
        description="Numero de projetos a pular para paginacao"
    ),
    continuation_token: Optional[str] = Query(
        None,
        description="Token de continuacao para buscar proxima pagina"
    )
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

        service = AzureDevOpsService(
            organization=org,
            project_name="",
            pat=token
        )

        return await service.get_projects(
            top=top,
            skip=skip,
            continuation_token=continuation_token
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar projetos: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
