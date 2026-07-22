from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import ExpModel, ProjectModel


class ExpRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, exp: ExpModel) -> ExpModel:
        self._session.add(exp)
        self._session.flush()
        self._session.refresh(exp)
        return exp

    def commit(self) -> None:
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def rollback(self) -> None:
        self._session.rollback()

    def get_by_id(self, exp_id: int) -> Optional[ExpModel]:
        return self._session.get(ExpModel, exp_id)

    def get_by_project_path(self, project_id: int, relative_path: str) -> Optional[ExpModel]:
        stmt = select(ExpModel).where(
            ExpModel.project_id == project_id,
            ExpModel.relative_path == relative_path,
        )
        return self._session.scalar(stmt)

    def get_by_project_version(self, project_id: int, version: str) -> Optional[ExpModel]:
        stmt = select(ExpModel).where(
            ExpModel.project_id == project_id,
            ExpModel.version == version,
        )
        return self._session.scalar(stmt)

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        project_id: Optional[int] = None,
        review_status: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> Tuple[List[ExpModel], int]:
        stmt = select(ExpModel)
        count_stmt = select(func.count()).select_from(ExpModel)
        if project_id is not None:
            stmt = stmt.where(ExpModel.project_id == project_id)
            count_stmt = count_stmt.where(ExpModel.project_id == project_id)
        if review_status:
            stmt = stmt.where(ExpModel.review_status == review_status)
            count_stmt = count_stmt.where(ExpModel.review_status == review_status)
        if model_type:
            stmt = stmt.join(ProjectModel, ProjectModel.id == ExpModel.project_id).where(
                ProjectModel.model_type == model_type
            )
            count_stmt = count_stmt.join(
                ProjectModel, ProjectModel.id == ExpModel.project_id
            ).where(ProjectModel.model_type == model_type)
        offset = max(page - 1, 0) * page_size
        stmt = stmt.order_by(ExpModel.id.desc()).offset(offset).limit(page_size)
        return list(self._session.scalars(stmt)), int(self._session.scalar(count_stmt) or 0)
