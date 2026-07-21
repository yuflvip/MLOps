"""add project exp root path

Revision ID: c7424db3e781
Revises: 9a5e6dc29e94
"""

from alembic import op
import sqlalchemy as sa


revision = "c7424db3e781"
down_revision = "9a5e6dc29e94"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("exp_root_path", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "exp_root_path")
