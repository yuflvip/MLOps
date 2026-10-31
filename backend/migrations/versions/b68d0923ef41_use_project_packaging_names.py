"""derive packaging filenames from model family key"""
import json
from alembic import op
import sqlalchemy as sa

revision = "b68d0923ef41"
down_revision = "a57c9812de30"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, project, packaging_json FROM projects")).fetchall()
    for row in rows:
        config = json.loads(row.packaging_json or "{}")
        config.pop("package_key", None)
        config["cfg_filename"] = row.project + ".cfg"
        config["names_filename"] = row.project + ".names"
        connection.execute(sa.text("UPDATE projects SET packaging_json=:config WHERE id=:id"),
                           {"id": row.id, "config": json.dumps(config, ensure_ascii=False)})


def downgrade():
    # Removed identifiers cannot be recovered; preserve current configuration.
    pass
