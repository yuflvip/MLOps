from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import TaskModel


class TaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, task: TaskModel) -> TaskModel:
        self.session.add(task)
        self.session.flush()
        self.session.refresh(task)
        return task

    def save(self, task: TaskModel) -> TaskModel:
        saved_task = self.session.merge(task)
        self.session.flush()
        self.session.refresh(saved_task)
        return saved_task

    def commit(self) -> None:
        self.session.commit()

    def get_by_id(self, task_id: int) -> Optional[TaskModel]:
        return self.session.get(TaskModel, task_id)

    def get_by_clearml_task_id(self, clearml_task_id: str) -> Optional[TaskModel]:
        stmt = select(TaskModel).where(TaskModel.clearml_task_id == clearml_task_id)
        return self.session.scalar(stmt)

    def list_by_parent_task_id(self, parent_task_id: int) -> List[TaskModel]:
        stmt = (
            select(TaskModel)
            .where(TaskModel.parent_task_id == parent_task_id)
            .order_by(TaskModel.id.asc())
        )
        return list(self.session.scalars(stmt))

    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        task_group: Optional[str] = None,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[TaskModel], int]:
        offset = max(page - 1, 0) * page_size
        stmt = select(TaskModel)
        count_stmt = select(func.count()).select_from(TaskModel)

        if task_group is not None:
            stmt = stmt.where(TaskModel.task_group == task_group)
            count_stmt = count_stmt.where(TaskModel.task_group == task_group)
        if task_type is not None:
            stmt = stmt.where(TaskModel.task_type == task_type)
            count_stmt = count_stmt.where(TaskModel.task_type == task_type)
        if status is not None:
            stmt = stmt.where(TaskModel.status == status)
            count_stmt = count_stmt.where(TaskModel.status == status)

        stmt = stmt.order_by(TaskModel.id.desc()).offset(offset).limit(page_size)
        items = list(self.session.scalars(stmt))
        total = self.session.scalar(count_stmt) or 0
        return items, int(total)
