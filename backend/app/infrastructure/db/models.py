from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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


class DatasetModel(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    task_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    class_names_json: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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


class QuantizationDatasetModel(Base):
    __tablename__ = "quantization_datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    image_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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


class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    model_architecture: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    exp_root_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    packaging_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dataset_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    epochs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    batch: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    imgsz: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
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


class ExpModel(Base):
    __tablename__ = "exps"
    __table_args__ = (
        UniqueConstraint("project_id", "relative_path", name="uq_exps_project_path"),
        UniqueConstraint("project_id", "version", name="uq_exps_project_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_path: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending_review", index=True
    )
    model_framework: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    model_size: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )


class ModelConversionModel(Base):
    __tablename__ = "model_conversions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exp_id: Mapped[int] = mapped_column(ForeignKey("exps.id"), nullable=False, index=True)
    parent_conversion_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("model_conversions.id"), nullable=True, index=True
    )
    converter_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_file: Mapped[str] = mapped_column(Text, nullable=False)
    source_format: Mapped[str] = mapped_column(String(32), nullable=False)
    target_platform: Mapped[str] = mapped_column(String(32), nullable=False)
    target_format: Mapped[str] = mapped_column(String(32), nullable=False)
    output_file: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    params_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    result_files_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    log_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class RuntimeEnvironmentModel(Base):
    __tablename__ = "runtime_environments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    env_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    python_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    working_dir: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    docker_image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_env_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
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


class WeightPackageModel(Base):
    __tablename__ = "weight_packages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    package_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    exp_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    project_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    exp_name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    runtime: Mapped[str] = mapped_column(String(32), nullable=False)
    model_framework: Mapped[str] = mapped_column(String(32), nullable=False)
    model_size: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    model_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    training_finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    training_date: Mapped[str] = mapped_column(String(8), nullable=False)
    source_file: Mapped[str] = mapped_column(Text, nullable=False)
    local_path: Mapped[str] = mapped_column(Text, nullable=False)
    unpacked_path: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    ftp_uploaded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ftp_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ftp_uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    upload_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    upload_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
