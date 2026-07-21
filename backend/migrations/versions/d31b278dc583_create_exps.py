"""create exps

Revision ID: d31b278dc583
Revises: c7424db3e781
"""

from alembic import op
import sqlalchemy as sa


revision = "d31b278dc583"
down_revision = "c7424db3e781"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("resolved_path", sa.Text(), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "relative_path", name="uq_exps_project_path"),
        sa.UniqueConstraint("project_id", "version", name="uq_exps_project_version"),
    )
    op.create_index(op.f("ix_exps_name"), "exps", ["name"], unique=False)
    op.create_index(op.f("ix_exps_project_id"), "exps", ["project_id"], unique=False)
    op.create_index(op.f("ix_exps_review_status"), "exps", ["review_status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_exps_review_status"), table_name="exps")
    op.drop_index(op.f("ix_exps_project_id"), table_name="exps")
    op.drop_index(op.f("ix_exps_name"), table_name="exps")
    op.drop_table("exps")
