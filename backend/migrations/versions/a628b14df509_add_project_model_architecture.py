"""add project model architecture

Revision ID: a628b14df509
Revises: f317e8042ac9
"""

from alembic import op
import sqlalchemy as sa


revision = "a628b14df509"
down_revision = "f317e8042ac9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("model_architecture", sa.String(length=32), nullable=True),
    )
    op.create_index(
        op.f("ix_projects_model_architecture"),
        "projects",
        ["model_architecture"],
        unique=False,
    )
    op.execute("UPDATE projects SET model_architecture = 'unknown'")


def downgrade() -> None:
    op.drop_index(op.f("ix_projects_model_architecture"), table_name="projects")
    op.drop_column("projects", "model_architecture")
