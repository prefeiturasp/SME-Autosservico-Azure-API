from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class WorkItemFilters(BaseModel):
    work_item_types: Optional[List[str]] = Field(None, description="Tipos de work items (Bug, Task, User Story, etc.)")
    states: Optional[List[str]] = Field(None, description="Estados (New, Active, Resolved, Closed, etc.)")
    area_paths: Optional[List[str]] = Field(None, description="Caminhos de área específicos")
    iteration_paths: Optional[List[str]] = Field(None, description="Caminhos de iteração específicos")
    assigned_to: Optional[List[str]] = Field(None, description="Usuários atribuídos")
    tags: Optional[str] = Field(None, description="Tags específicas")

    def summarize(self) -> str:
        """Gera resumo seguro dos filtros sem expor dados sensíveis."""
        parts = []
        if self.work_item_types:
            parts.append(f"types={len(self.work_item_types)}")
        if self.states:
            parts.append(f"states={len(self.states)}")
        if self.area_paths:
            parts.append(f"areas={len(self.area_paths)}")
        if self.iteration_paths:
            parts.append(f"iterations={len(self.iteration_paths)}")
        if self.assigned_to:
            parts.append(f"assignees={len(self.assigned_to)}")
        if self.tags:
            parts.append("tags=1")
        return "|".join(parts) if parts else "none"

class WorkItemRequest(BaseModel):
    organization: Optional[str] = Field(None,
                                        description="Nome da organização no Azure DevOps (usa padrão do .env se não informado)")
    project_name: str = Field(..., description="Nome do projeto")
    pat: Optional[str] = Field(None, description="Personal Access Token (usa padrão do .env se não informado)")
    start_date: Optional[str] = Field(None, description="Data inicial (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Data final (YYYY-MM-DD)")
    year: Optional[int] = Field(None, description="Ano para busca por mês")
    month: Optional[int] = Field(None, description="Mês (1-12) para busca por mês")
    filters: Optional[WorkItemFilters] = Field(None, description="Filtros adicionais para refinar a busca")

class WorkItemResponse(BaseModel):
    id: int
    title: str
    state: Optional[str]
    work_item_type: Optional[str]
    tags: Optional[str]
    created_by: Optional[str]
    assigned_to: Optional[str]
    area_path: Optional[str]
    team_project: Optional[str]
    iteration_path: Optional[str]
    completed_work: Optional[float]
    original_estimate: Optional[float]
    start_date: Optional[str]
    finish_date: Optional[str]
    created_date: Optional[str]
    changed_date: Optional[str]
    closed_date: Optional[str]
    parent_id: Optional[int]
    parent_link: Optional[str]

class BacklogResponse(BaseModel):
    total_items: int
    parents: List[WorkItemResponse]
    children: List[WorkItemResponse]
    metadata: Dict[str, Any]

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None