"""add model family packaging configuration"""
from alembic import op
import sqlalchemy as sa

revision = "a57c9812de30"
down_revision = "f4d2c8a17b63"
branch_labels = None
depends_on = None


def upgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("projects")}
    if "packaging_json" not in columns:
        op.add_column("projects", sa.Column("packaging_json", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("projects", "packaging_json")
