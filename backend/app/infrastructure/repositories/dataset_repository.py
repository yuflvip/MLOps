from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import DatasetModel


class DatasetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, dataset: DatasetModel) -> DatasetModel:
        try:
            self._session.add(dataset)
            self._session.flush()
            self._session.refresh(dataset)
            return dataset
        except Exception:
            self._session.rollback()
            raise

    def save(self, dataset: DatasetModel) -> DatasetModel:
        try:
            saved_dataset = self._session.merge(dataset)
            self._session.flush()
            self._session.refresh(saved_dataset)
            return saved_dataset
        except Exception:
            self._session.rollback()
            raise

    def delete(self, dataset: DatasetModel) -> None:
        try:
            self._session.delete(dataset)
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

    def get_by_id(self, dataset_id: int) -> Optional[DatasetModel]:
        return self._session.get(DatasetModel, dataset_id)

    def get_by_name(self, name: str) -> Optional[DatasetModel]:
        stmt = select(DatasetModel).where(DatasetModel.name == name)
        return self._session.scalar(stmt)

    def get_by_path(self, path: str) -> Optional[DatasetModel]:
        stmt = select(DatasetModel).where(DatasetModel.path == path)
        return self._session.scalar(stmt)

    def list_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        name: Optional[str] = None,
        path: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> Tuple[List[DatasetModel], int]:
        stmt = select(DatasetModel)
        count_stmt = select(func.count()).select_from(DatasetModel)
        if name:
            stmt = stmt.where(DatasetModel.name.ilike(f"%{name}%"))
            count_stmt = count_stmt.where(DatasetModel.name.ilike(f"%{name}%"))
        if path:
            stmt = stmt.where(DatasetModel.path.ilike(f"%{path}%"))
            count_stmt = count_stmt.where(DatasetModel.path.ilike(f"%{path}%"))
        if task_type:
            stmt = stmt.where(DatasetModel.task_type == task_type)
            count_stmt = count_stmt.where(DatasetModel.task_type == task_type)
        offset = max(page - 1, 0) * page_size
        stmt = stmt.order_by(DatasetModel.id.desc()).offset(offset).limit(page_size)
        items = list(self._session.scalars(stmt))
        total = self._session.scalar(count_stmt) or 0
        return items, int(total)
