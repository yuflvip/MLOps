"""add exp review comment

Revision ID: e84c190ab642
Revises: d31b278dc583
"""

from alembic import op
import sqlalchemy as sa


revision = "e84c190ab642"
down_revision = "d31b278dc583"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("exps", sa.Column("review_comment", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("exps", "review_comment")
