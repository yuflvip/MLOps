"""snapshot model type and training finish time on packages"""
from datetime import datetime, timezone
from pathlib import Path
from alembic import op
import sqlalchemy as sa
revision = "e91a3256bc74"
down_revision = "d80f2145ab63"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    columns = {column["name"] for column in sa.inspect(connection).get_columns("weight_packages")}
    if "model_type" not in columns:
        op.add_column("weight_packages", sa.Column("model_type", sa.String(32), nullable=True))
        op.create_index("ix_weight_packages_model_type", "weight_packages", ["model_type"])
    if "training_finished_at" not in columns:
        op.add_column("weight_packages", sa.Column("training_finished_at", sa.DateTime(), nullable=True))
    rows = connection.execute(sa.text("SELECT w.id, p.model_type, e.resolved_path FROM weight_packages w LEFT JOIN projects p ON p.id=w.project_id LEFT JOIN exps e ON e.id=w.exp_id")).fetchall()
    for row in rows:
        finished = None
        if row.resolved_path:
            try:
                stat = (Path(row.resolved_path) / "results.png").stat()
                finished = datetime.fromtimestamp(getattr(stat, "st_birthtime", stat.st_mtime), timezone.utc).replace(tzinfo=None)
            except OSError:
                pass
        connection.execute(sa.text("UPDATE weight_packages SET model_type=:model_type, training_finished_at=:finished WHERE id=:id"), {"id": row.id, "model_type": row.model_type, "finished": finished})


def downgrade():
    op.drop_column("weight_packages", "training_finished_at")
    op.drop_index("ix_weight_packages_model_type", table_name="weight_packages")
    op.drop_column("weight_packages", "model_type")
