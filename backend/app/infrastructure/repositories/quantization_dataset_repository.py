from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import QuantizationDatasetModel


class QuantizationDatasetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, dataset: QuantizationDatasetModel) -> QuantizationDatasetModel:
        self._session.add(dataset)
        self._session.flush()
        return dataset

    def get_by_id(self, dataset_id: int) -> Optional[QuantizationDatasetModel]:
        return self._session.get(QuantizationDatasetModel, dataset_id)

    def get_by_name(self, name: str) -> Optional[QuantizationDatasetModel]:
        stmt = select(QuantizationDatasetModel).where(
            QuantizationDatasetModel.name == name
        )
        return self._session.scalar(stmt)

    def list_paginated(
        self, *, page: int, page_size: int, name: Optional[str]
    ) -> Tuple[List[QuantizationDatasetModel], int]:
        stmt = select(QuantizationDatasetModel)
        count_stmt = select(func.count()).select_from(QuantizationDatasetModel)
        if name:
            condition = QuantizationDatasetModel.name.ilike(f"%{name}%")
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)
        items = list(
            self._session.scalars(
                stmt.order_by(QuantizationDatasetModel.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, int(self._session.scalar(count_stmt) or 0)

    def delete(self, dataset: QuantizationDatasetModel) -> None:
        self._session.delete(dataset)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
