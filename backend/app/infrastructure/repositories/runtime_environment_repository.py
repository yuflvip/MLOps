from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import RuntimeEnvironmentModel


class RuntimeEnvironmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, runtime_environment: RuntimeEnvironmentModel) -> RuntimeEnvironmentModel:
        try:
            self._session.add(runtime_environment)
            self._session.flush()
            self._session.refresh(runtime_environment)
            return runtime_environment
        except Exception:
            self._session.rollback()
            raise

    def save(self, runtime_environment: RuntimeEnvironmentModel) -> RuntimeEnvironmentModel:
        try:
            saved_runtime_environment = self._session.merge(runtime_environment)
            self._session.flush()
            self._session.refresh(saved_runtime_environment)
            return saved_runtime_environment
        except Exception:
            self._session.rollback()
            raise

    def delete(self, runtime_environment: RuntimeEnvironmentModel) -> None:
        try:
            self._session.delete(runtime_environment)
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

    def get_by_id(self, runtime_environment_id: int) -> Optional[RuntimeEnvironmentModel]:
        return self._session.get(RuntimeEnvironmentModel, runtime_environment_id)

    def get_by_code(self, code: str) -> Optional[RuntimeEnvironmentModel]:
        stmt = select(RuntimeEnvironmentModel).where(RuntimeEnvironmentModel.code == code)
        return self._session.scalar(stmt)

    def list_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        code: Optional[str] = None,
        name: Optional[str] = None,
        env_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[RuntimeEnvironmentModel], int]:
        stmt = select(RuntimeEnvironmentModel)
        count_stmt = select(func.count()).select_from(RuntimeEnvironmentModel)
        if code:
            stmt = stmt.where(RuntimeEnvironmentModel.code.ilike(f"%{code}%"))
            count_stmt = count_stmt.where(RuntimeEnvironmentModel.code.ilike(f"%{code}%"))
        if name:
            stmt = stmt.where(RuntimeEnvironmentModel.name.ilike(f"%{name}%"))
            count_stmt = count_stmt.where(RuntimeEnvironmentModel.name.ilike(f"%{name}%"))
        if env_type:
            stmt = stmt.where(RuntimeEnvironmentModel.env_type == env_type)
            count_stmt = count_stmt.where(RuntimeEnvironmentModel.env_type == env_type)
        if is_active is not None:
            stmt = stmt.where(RuntimeEnvironmentModel.is_active == is_active)
            count_stmt = count_stmt.where(RuntimeEnvironmentModel.is_active == is_active)
        offset = max(page - 1, 0) * page_size
        stmt = stmt.order_by(RuntimeEnvironmentModel.id.desc()).offset(offset).limit(page_size)
        items = list(self._session.scalars(stmt))
        total = self._session.scalar(count_stmt) or 0
        return items, int(total)
