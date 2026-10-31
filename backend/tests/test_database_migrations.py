import unittest
from pathlib import Path

from sqlalchemy import create_engine, inspect

from app.infrastructure.db import Base
from app.infrastructure.db.migrations import initialize_database

CONFIG = Path(__file__).resolve().parents[1] / "config" / "app.yaml"


class DatabaseMigrationTests(unittest.TestCase):
    def test_fresh_database_and_repeated_startup(self):
        engine = create_engine("sqlite:///:memory:")
        initialize_database(engine, CONFIG)
        initialize_database(engine, CONFIG)
        with engine.connect() as connection:
            self.assertEqual(connection.exec_driver_sql("select version_num from alembic_version").scalar(), "e91a3256bc74")
        self.assertIn("packaging_json", {c["name"] for c in inspect(engine).get_columns("projects")})

    def test_upgrade_preserves_existing_records(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.exec_driver_sql("ALTER TABLE projects DROP COLUMN packaging_json")
            connection.exec_driver_sql("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)")
            connection.exec_driver_sql("INSERT INTO alembic_version VALUES ('f4d2c8a17b63')")
            connection.exec_driver_sql("INSERT INTO projects (project, name, dataset_ids_json, created_at, updated_at) VALUES ('existing', 'existing', '[]', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)")
        initialize_database(engine, CONFIG)
        initialize_database(engine, CONFIG)
        with engine.connect() as connection:
            self.assertEqual(connection.exec_driver_sql("SELECT project FROM projects").scalar(), "existing")
            self.assertEqual(connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar(), "e91a3256bc74")


if __name__ == "__main__":
    unittest.main()
