import aiohttp
import logging
import os
import time
from fastapi import HTTPException
from typing import Dict, Any, Optional, List
from schemas.backlog import WorkItemResponse, BacklogResponse, WorkItemFilters
from schemas.project import ProjectResponse, ProjectsListResponse
from utils.helpers import (
    format_date,
    generate_work_item_url,
    create_auth_headers,
    get_first_and_last_day_of_month
)

logger = logging.getLogger("azure_devops.service")

class AzureDevOpsService:
    def __init__(self, organization: str, project_name: str, pat: str):
        self.organization = organization
        self.project_name = project_name
        self.pat = pat
        self.headers = create_auth_headers(pat)
        self.base_url = os.getenv("AZURE_DEVOPS_API_URL", "http://localhost:8000")

    async def get_projects(
        self,
        top: int = 100,
        skip: int = 0,
        continuation_token: Optional[str] = None
    ) -> ProjectsListResponse:
        start = time.perf_counter()
        url = f"https://dev.azure.com/{self.organization}/_apis/projects"
        params: Dict[str, Any] = {
            "api-version": "7.0",
            "$top": top,
            "$skip": skip
        }
        
        if continuation_token:
            params["continuationToken"] = continuation_token

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Erro ao buscar projetos: {response.status} - {error_text}")
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Erro ao buscar projetos do Azure DevOps: {error_text}"
                    )
                
                data = await response.json()
                next_token = response.headers.get("x-ms-continuationtoken")

                projects = [
                    ProjectResponse(
                        id=project.get("id", ""),
                        name=project.get("name", ""),
                        description=project.get("description"),
                        url=project.get("url"),
                        state=project.get("state"),
                        revision=project.get("revision"),
                        visibility=project.get("visibility"),
                        last_update_time=project.get("lastUpdateTime")
                    )
                    for project in data.get("value", [])
                ]

                duration_ms = (time.perf_counter() - start) * 1000
                logger.info(
                    "Projects fetched | org=%s count=%s total=%s has_more=%s duration_ms=%.1f",
                    self.organization,
                    len(projects),
                    data.get("count"),
                    next_token is not None,
                    duration_ms
                )

                return ProjectsListResponse(
                    count=len(projects),
                    total_count=data.get("count"),
                    projects=projects,
                    continuation_token=next_token,
                    has_more=next_token is not None
                )

    async def get_backlog_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        filters: Optional[WorkItemFilters] = None
    ) -> BacklogResponse:
        start = time.perf_counter()
        logger.info(
            "Backlog fetch started | org=%s project=%s start=%s end=%s filters=%s",
            self.organization,
            self.project_name,
            start_date or "none",
            end_date or "none",
            filters.summarize() if filters else "none"
        )

        work_item_ids = await self._query_work_items(start_date, end_date, filters)
        
        if not work_item_ids:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "Backlog empty | org=%s project=%s start=%s end=%s duration_ms=%.1f",
                self.organization,
                self.project_name,
                start_date,
                end_date,
                duration_ms
            )
            return BacklogResponse(
                total_items=0,
                parents=[],
                children=[],
                metadata={
                    "start_date": start_date or "none",
                    "end_date": end_date or "none",
                    "organization": self.organization,
                    "project": self.project_name
                }
            )
        
        work_items = await self._get_work_items_details(work_item_ids)
        parents, children = self._categorize_work_items(work_items)

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Backlog fetched | org=%s project=%s items=%s parents=%s children=%s duration_ms=%.1f",
            self.organization,
            self.project_name,
            len(work_items),
            len(parents),
            len(children),
            duration_ms
        )

        return BacklogResponse(
            total_items=len(work_items),
            parents=parents,
            children=children,
            metadata={
                "start_date": start_date or "none",
                "end_date": end_date or "none",
                "organization": self.organization,
                "project": self.project_name,
                "total_parents": len(parents),
                "total_children": len(children)
            }
        )

    def _build_filter_clauses(self, filters: WorkItemFilters) -> List[str]:
        """Builds WIQL filter clauses from WorkItemFilters."""
        clauses = []
        
        if filters.work_item_types:
            types = ", ".join(f"'{t}'" for t in filters.work_item_types)
            clauses.append(f"[System.WorkItemType] IN ({types})")
        
        if filters.states:
            states = ", ".join(f"'{s}'" for s in filters.states)
            clauses.append(f"[System.State] IN ({states})")
        
        if filters.area_paths:
            clauses.extend(f"[System.AreaPath] UNDER '{area}'" for area in filters.area_paths)
        
        if filters.iteration_paths:
            clauses.extend(f"[System.IterationPath] UNDER '{it}'" for it in filters.iteration_paths)
        
        if filters.assigned_to:
            users = ", ".join(f"'{u}'" for u in filters.assigned_to)
            clauses.append(f"[System.AssignedTo] IN ({users})")
        
        if filters.tags:
            clauses.append(f"[System.Tags] CONTAINS '{filters.tags}'")
        
        return clauses

    async def _query_work_items(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        filters: Optional[WorkItemFilters] = None
    ) -> List[int]:
        start = time.perf_counter()
        url = f"https://dev.azure.com/{self.organization}/{self.project_name}/_apis/wit/wiql"
        params = {
            "api-version": "7.0",
            "$top": 20000  # Garantir que todos os resultados sejam retornados
        }

        where_clauses = [
            f"[System.TeamProject] = '{self.project_name}'"
        ]

        # Only add date filters if specified
        if start_date:
            where_clauses.append(f"[System.CreatedDate] >= '{start_date}'")
        if end_date:
            where_clauses.append(f"[System.CreatedDate] <= '{end_date}'")

        if filters:
            where_clauses.extend(self._build_filter_clauses(filters))

        wiql = f"SELECT [System.Id] FROM WorkItems WHERE {' AND '.join(where_clauses)} ORDER BY [System.CreatedDate] DESC"

        # Log da query WIQL para debug
        logger.info("WIQL Query: %s", wiql)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=self.headers,
                params=params,
                json={"query": wiql}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Erro na query WIQL: {response.status} - {error_text}")
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Erro ao consultar work items: {error_text}"
                    )
                
                data = await response.json()
                ids = [item["id"] for item in data.get("workItems", [])]

                duration_ms = (time.perf_counter() - start) * 1000
                logger.info(
                    "WIQL query executed | org=%s project=%s ids=%s duration_ms=%.1f",
                    self.organization,
                    self.project_name,
                    len(ids),
                    duration_ms
                )
                return ids

    async def _get_work_items_details(self, work_item_ids: List[int]) -> List[Dict[str, Any]]:
        if not work_item_ids:
            return []
        
        all_items = []
        batch_size = 200
        start = time.perf_counter()
        
        for i in range(0, len(work_item_ids), batch_size):
            batch_ids = work_item_ids[i:i + batch_size]
            ids_str = ",".join(str(id) for id in batch_ids)
            
            url = f"https://dev.azure.com/{self.organization}/{self.project_name}/_apis/wit/workitems"
            params = {
                "ids": ids_str,
                "api-version": "7.0",
                "$expand": "relations"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Erro ao buscar detalhes: {response.status} - {error_text}")
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Erro ao buscar detalhes dos work items: {error_text}"
                        )
                    
                    data = await response.json()
                    all_items.extend(data.get("value", []))

                    logger.info(
                        "Fetched work item batch | org=%s project=%s batch_size=%s accumulated=%s",
                        self.organization,
                        self.project_name,
                        len(batch_ids),
                        len(all_items)
                    )
        
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Work item details fetched | org=%s project=%s total=%s duration_ms=%.1f",
            self.organization,
            self.project_name,
            len(all_items),
            duration_ms
        )

        return all_items

    def _extract_parent_info(self, relations: Optional[List[Dict]]) -> tuple[Optional[int], Optional[str]]:
        """Extracts parent ID and link from work item relations."""
        if not relations:
            return None, None
        
        for rel in relations:
            if rel.get("rel") == "System.LinkTypes.Hierarchy-Reverse":
                parent_url = rel.get("url", "")
                if parent_url:
                    return int(parent_url.split("/")[-1]), parent_url
                break
        
        return None, None

    def _get_display_name(self, field_value: Any) -> Optional[str]:
        """Safely extracts displayName from a field that may be a dict or None."""
        if isinstance(field_value, dict):
            return field_value.get("displayName")
        return None

    def _create_work_item_response(self, item: Dict[str, Any]) -> WorkItemResponse:
        """Creates a WorkItemResponse from a raw work item dict."""
        fields = item.get("fields", {})
        parent_id, parent_link = self._extract_parent_info(item.get("relations"))
        
        return WorkItemResponse(
            id=item.get("id"),
            title=fields.get("System.Title", ""),
            state=fields.get("System.State"),
            work_item_type=fields.get("System.WorkItemType", ""),
            tags=fields.get("System.Tags"),
            created_by=self._get_display_name(fields.get("System.CreatedBy")),
            assigned_to=self._get_display_name(fields.get("System.AssignedTo")),
            area_path=fields.get("System.AreaPath"),
            team_project=fields.get("System.TeamProject"),
            iteration_path=fields.get("System.IterationPath"),
            completed_work=fields.get("Microsoft.VSTS.Scheduling.CompletedWork"),
            original_estimate=fields.get("Microsoft.VSTS.Scheduling.OriginalEstimate"),
            start_date=format_date(fields.get("Microsoft.VSTS.Scheduling.StartDate")),
            finish_date=format_date(fields.get("Microsoft.VSTS.Scheduling.FinishDate")),
            created_date=format_date(fields.get("System.CreatedDate")),
            changed_date=format_date(fields.get("System.ChangedDate")),
            closed_date=format_date(fields.get("Microsoft.VSTS.Common.ClosedDate")),
            parent_id=parent_id,
            parent_link=parent_link
        )

    def _categorize_work_items(
        self, work_items: List[Dict[str, Any]]
    ) -> tuple[List[WorkItemResponse], List[WorkItemResponse]]:
        """Categorizes work items into parents and children based on type."""
        parent_types = {"Epic", "Feature", "User Story", "Product Backlog Item"}
        parents = []
        children = []
        
        for item in work_items:
            work_item_response = self._create_work_item_response(item)
            target_list = parents if work_item_response.work_item_type in parent_types else children
            target_list.append(work_item_response)
        
        return parents, children
