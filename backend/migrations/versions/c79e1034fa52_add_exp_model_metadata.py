"""store experiment model framework and input size"""
from alembic import op
import sqlalchemy as sa
revision = "c79e1034fa52"
down_revision = "b68d0923ef41"
branch_labels = None
depends_on = None


def upgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("exps")}
    for name in ("model_framework", "model_size"):
        if name not in columns:
            op.add_column("exps", sa.Column(name, sa.String(32), nullable=True))


def downgrade():
    op.drop_column("exps", "model_size")
    op.drop_column("exps", "model_framework")
