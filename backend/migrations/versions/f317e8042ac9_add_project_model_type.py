"""add project model type

Revision ID: f317e8042ac9
Revises: e84c190ab642
"""

import json

from alembic import op
import sqlalchemy as sa


revision = "f317e8042ac9"
down_revision = "e84c190ab642"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("model_type", sa.String(length=32), nullable=True))
    op.create_index(op.f("ix_projects_model_type"), "projects", ["model_type"], unique=False)
    connection = op.get_bind()
    dataset_types = {
        row.id: row.task_type
        for row in connection.execute(sa.text("SELECT id, task_type FROM datasets"))
    }
    for row in connection.execute(sa.text("SELECT id, dataset_ids_json FROM projects")):
        dataset_ids = json.loads(row.dataset_ids_json or "[]")
        model_types = {
            dataset_types.get(dataset_id)
            for dataset_id in dataset_ids
            if dataset_types.get(dataset_id)
        }
        if len(model_types) == 1:
            connection.execute(
                sa.text("UPDATE projects SET model_type = :model_type WHERE id = :id"),
                {"model_type": model_types.pop(), "id": row.id},
            )


def downgrade() -> None:
    op.drop_index(op.f("ix_projects_model_type"), table_name="projects")
    op.drop_column("projects", "model_type")
