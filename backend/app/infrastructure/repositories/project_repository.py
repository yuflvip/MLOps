from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import ProjectModel


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, project: ProjectModel) -> ProjectModel:
        try:
            self._session.add(project)
            self._session.flush()
            self._session.refresh(project)
            return project
        except Exception:
            self._session.rollback()
            raise

    def save(self, project: ProjectModel) -> ProjectModel:
        try:
            saved_project = self._session.merge(project)
            self._session.flush()
            self._session.refresh(saved_project)
            return saved_project
        except Exception:
            self._session.rollback()
            raise

    def delete(self, project: ProjectModel) -> None:
        try:
            self._session.delete(project)
            self._session.flush()
        except Exception:
            self._session.rollback()
            raise

    def commit(self) -> None:
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def get_by_id(self, project_id: int) -> Optional[ProjectModel]:
        return self._session.get(ProjectModel, project_id)

    def get_by_project(self, project: str) -> Optional[ProjectModel]:
        stmt = select(ProjectModel).where(ProjectModel.project == project)
        return self._session.scalar(stmt)

    def list_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        project: Optional[str] = None,
        name: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> Tuple[List[ProjectModel], int]:
        stmt = select(ProjectModel)
        count_stmt = select(func.count()).select_from(ProjectModel)
        if project:
            stmt = stmt.where(ProjectModel.project.ilike(f"%{project}%"))
            count_stmt = count_stmt.where(ProjectModel.project.ilike(f"%{project}%"))
        if name:
            stmt = stmt.where(ProjectModel.name.ilike(f"%{name}%"))
            count_stmt = count_stmt.where(ProjectModel.name.ilike(f"%{name}%"))
        if model_type:
            stmt = stmt.where(ProjectModel.model_type == model_type)
            count_stmt = count_stmt.where(ProjectModel.model_type == model_type)
        offset = max(page - 1, 0) * page_size
        stmt = stmt.order_by(ProjectModel.id.desc()).offset(offset).limit(page_size)
        items = list(self._session.scalars(stmt))
        total = self._session.scalar(count_stmt) or 0
        return items, int(total)
