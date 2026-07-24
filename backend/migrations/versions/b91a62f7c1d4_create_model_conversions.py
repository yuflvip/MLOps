"""create model conversions

Revision ID: b91a62f7c1d4
Revises: a628b14df509
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b91a62f7c1d4"
down_revision: Union[str, None] = "a628b14df509"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_conversions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("exp_id", sa.Integer(), nullable=False),
        sa.Column("parent_conversion_id", sa.Integer(), nullable=True),
        sa.Column("converter_code", sa.String(length=64), nullable=False),
        sa.Column("source_file", sa.Text(), nullable=False),
        sa.Column("source_format", sa.String(length=32), nullable=False),
        sa.Column("target_platform", sa.String(length=32), nullable=False),
        sa.Column("target_format", sa.String(length=32), nullable=False),
        sa.Column("output_file", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("params_json", sa.Text(), nullable=False),
        sa.Column("result_files_json", sa.Text(), nullable=False),
        sa.Column("log_path", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["exp_id"], ["exps.id"]),
        sa.ForeignKeyConstraint(["parent_conversion_id"], ["model_conversions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_model_conversions_exp_id"), "model_conversions", ["exp_id"]
    )
    op.create_index(
        op.f("ix_model_conversions_parent_conversion_id"),
        "model_conversions",
        ["parent_conversion_id"],
    )
    op.create_index(
        op.f("ix_model_conversions_converter_code"),
        "model_conversions",
        ["converter_code"],
    )
    op.create_index(
        op.f("ix_model_conversions_status"), "model_conversions", ["status"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_model_conversions_status"), table_name="model_conversions")
    op.drop_index(
        op.f("ix_model_conversions_converter_code"),
        table_name="model_conversions",
    )
    op.drop_index(
        op.f("ix_model_conversions_parent_conversion_id"),
        table_name="model_conversions",
    )
    op.drop_index(op.f("ix_model_conversions_exp_id"), table_name="model_conversions")
    op.drop_table("model_conversions")
