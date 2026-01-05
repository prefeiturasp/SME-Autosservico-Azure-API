from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ProjectResponse(BaseModel):
    """Representa um projeto do Azure DevOps"""
    id: str = Field(..., description="ID único do projeto")
    name: str = Field(..., description="Nome do projeto")
    description: Optional[str] = Field(None, description="Descrição do projeto")
    url: Optional[str] = Field(None, description="URL da API do projeto")
    state: Optional[str] = Field(None, description="Estado do projeto (wellFormed, etc.)")
    revision: Optional[int] = Field(None, description="Número da revisão")
    visibility: Optional[str] = Field(None, description="Visibilidade do projeto (private, public)")
    last_update_time: Optional[str] = Field(None, description="Data da última atualização")


class ProjectsListResponse(BaseModel):
    """Resposta paginada da listagem de projetos"""
    count: int = Field(..., description="Número total de projetos retornados nesta página")
    total_count: Optional[int] = Field(None, description="Número total de projetos disponíveis")
    projects: List[ProjectResponse] = Field(..., description="Lista de projetos")
    continuation_token: Optional[str] = Field(None, description="Token para buscar próxima página")
    has_more: bool = Field(False, description="Indica se há mais páginas disponíveis")
