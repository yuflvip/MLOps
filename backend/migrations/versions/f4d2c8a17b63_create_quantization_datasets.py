"""create quantization datasets

Revision ID: f4d2c8a17b63
Revises: b91a62f7c1d4
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4d2c8a17b63"
down_revision: Union[str, None] = "b91a62f7c1d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The application currently calls Base.metadata.create_all during startup.
    # If it has already created this new table, only advance Alembic's revision.
    if "quantization_datasets" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "quantization_datasets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("image_count", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path"),
    )
    op.create_index(
        op.f("ix_quantization_datasets_name"),
        "quantization_datasets",
        ["name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_quantization_datasets_name"),
        table_name="quantization_datasets",
    )
    op.drop_table("quantization_datasets")
