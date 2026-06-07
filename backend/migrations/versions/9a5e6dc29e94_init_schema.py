"""init schema

Revision ID: 9a5e6dc29e94
Revises: 
Create Date: 2026-06-06 19:52:07.849526

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '9a5e6dc29e94'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("parent_task_id", sa.Integer(), nullable=True),
        sa.Column("task_source", sa.String(length=32), nullable=False),
        sa.Column("clearml_task_id", sa.String(length=128), nullable=True),
        sa.Column("task_name", sa.String(length=255), nullable=False),
        sa.Column("task_group", sa.String(length=32), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("queue_name", sa.String(length=128), nullable=True),
        sa.Column("template_name", sa.String(length=128), nullable=True),
        sa.Column("params_json", sa.Text(), nullable=True),
        sa.Column("parameter_snapshot_json", sa.Text(), nullable=True),
        sa.Column("runtime_snapshot_json", sa.Text(), nullable=True),
        sa.Column("custom_data_json", sa.Text(), nullable=True),
        sa.Column("result_summary_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("last_sync_status", sa.String(length=32), nullable=True),
        sa.Column("last_sync_error", sa.Text(), nullable=True),
        sa.Column("sync_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clearml_task_id"),
    )
    op.create_index(op.f("ix_tasks_parent_task_id"), "tasks", ["parent_task_id"], unique=False)
    op.create_index(op.f("ix_tasks_queue_name"), "tasks", ["queue_name"], unique=False)
    op.create_index(op.f("ix_tasks_status"), "tasks", ["status"], unique=False)
    op.create_index(op.f("ix_tasks_task_group"), "tasks", ["task_group"], unique=False)
    op.create_index(op.f("ix_tasks_task_type"), "tasks", ["task_type"], unique=False)

    op.create_table(
        "task_artifacts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("parent_artifact_id", sa.Integer(), nullable=True),
        sa.Column("artifact_role", sa.String(length=64), nullable=False),
        sa.Column("artifact_name", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("file_uri", sa.Text(), nullable=True),
        sa.Column("format", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_artifact_id"], ["task_artifacts.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_task_artifacts_artifact_role"),
        "task_artifacts",
        ["artifact_role"],
        unique=False,
    )
    op.create_index(
        op.f("ix_task_artifacts_parent_artifact_id"),
        "task_artifacts",
        ["parent_artifact_id"],
        unique=False,
    )
    op.create_index(op.f("ix_task_artifacts_task_id"), "task_artifacts", ["task_id"], unique=False)

    op.create_table(
        "sync_checkpoints",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sync_scope", sa.String(length=64), nullable=False),
        sa.Column("last_cursor", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sync_scope"),
    )

    op.create_table(
        "job_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_name", sa.String(length=128), nullable=False),
        sa.Column("job_scope", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_runs_job_name"), "job_runs", ["job_name"], unique=False)
    op.create_index(op.f("ix_job_runs_status"), "job_runs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_job_runs_status"), table_name="job_runs")
    op.drop_index(op.f("ix_job_runs_job_name"), table_name="job_runs")
    op.drop_table("job_runs")

    op.drop_table("sync_checkpoints")

    op.drop_index(op.f("ix_task_artifacts_task_id"), table_name="task_artifacts")
    op.drop_index(op.f("ix_task_artifacts_parent_artifact_id"), table_name="task_artifacts")
    op.drop_index(op.f("ix_task_artifacts_artifact_role"), table_name="task_artifacts")
    op.drop_table("task_artifacts")

    op.drop_index(op.f("ix_tasks_task_type"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_task_group"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_status"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_queue_name"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_parent_task_id"), table_name="tasks")
    op.drop_table("tasks")
