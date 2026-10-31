"""create weight package records"""
from alembic import op
import sqlalchemy as sa
revision = "d80f2145ab63"
down_revision = "c79e1034fa52"
branch_labels = None
depends_on = None


def upgrade():
    if "weight_packages" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table("weight_packages",
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('package_name', sa.String(255), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('exp_id', sa.Integer(), nullable=False),
        sa.Column('project_key', sa.String(128), nullable=False),
        sa.Column('exp_name', sa.String(255), nullable=False),
        sa.Column('platform', sa.String(16), nullable=False),
        sa.Column('runtime', sa.String(32), nullable=False),
        sa.Column('model_framework', sa.String(32), nullable=False),
        sa.Column('model_size', sa.String(32), nullable=True),
        sa.Column('training_date', sa.String(8), nullable=False),
        sa.Column('source_file', sa.Text(), nullable=False),
        sa.Column('local_path', sa.Text(), nullable=False),
        sa.Column('unpacked_path', sa.Text(), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('sha256', sa.String(64), nullable=False),
        sa.Column('snapshot_json', sa.Text(), nullable=False),
        sa.Column('ftp_uploaded', sa.Boolean(), nullable=False),
        sa.Column('ftp_path', sa.Text(), nullable=True),
        sa.Column('ftp_uploaded_at', sa.DateTime(), nullable=True),
        sa.Column('upload_status', sa.String(16), nullable=False),
        sa.Column('upload_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("package_name"),
    )
    op.create_index("ix_weight_packages_project_id", "weight_packages", ["project_id"])
    op.create_index("ix_weight_packages_exp_id", "weight_packages", ["exp_id"])
    op.create_index("ix_weight_packages_project_key", "weight_packages", ["project_key"])
    op.create_index("ix_weight_packages_platform", "weight_packages", ["platform"])


def downgrade():
    op.drop_table("weight_packages")
