from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tasks.id"),
        index=True,
        nullable=True,
    )
    task_source: Mapped[str] = mapped_column(String(32), nullable=False)
    clearml_task_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        unique=True,
        nullable=True,
    )
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    task_group: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    queue_name: Mapped[Optional[str]] = mapped_column(
        String(128),
        index=True,
        nullable=True,
    )
    template_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    params_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parameter_snapshot_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    runtime_snapshot_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_summary_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_sync_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    last_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sync_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )
    parent: Mapped[Optional["TaskModel"]] = relationship(
        "TaskModel",
        remote_side="TaskModel.id",
        back_populates="children",
    )
    children: Mapped[List["TaskModel"]] = relationship(
        "TaskModel",
        back_populates="parent",
    )


class TaskArtifactModel(Base):
    __tablename__ = "task_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False, index=True)
    parent_artifact_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("task_artifacts.id"),
        index=True,
        nullable=True,
    )
    artifact_role: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    artifact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_uri: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )
    parent: Mapped[Optional["TaskArtifactModel"]] = relationship(
        "TaskArtifactModel",
        remote_side="TaskArtifactModel.id",
        back_populates="children",
    )
    children: Mapped[List["TaskArtifactModel"]] = relationship(
        "TaskArtifactModel",
        back_populates="parent",
    )


class SyncCheckpointModel(Base):
    __tablename__ = "sync_checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sync_scope: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    last_cursor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )


class JobRunModel(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_scope: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    details_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utcnow,
    )
