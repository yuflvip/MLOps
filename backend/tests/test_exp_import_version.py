import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.infrastructure.db import Base
from app.infrastructure.repositories.exp_repository import ExpRepository
from app.application.services.exp_service import ExpService
from app.domain.common.exceptions import ExpConflictError


class ImportVersionTests(unittest.TestCase):
    def test_import_approve_reject_and_conflict(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with tempfile.TemporaryDirectory() as tmp, Session(engine) as session:
            root = Path(tmp)
            for name in ("one", "two", "missing"):
                (root / name).mkdir()
            for name in ("one", "two"):
                (root / name / "results.png").write_bytes(b"image")
            service = ExpService(exp_repository=ExpRepository(session),
                project_repository=SimpleNamespace(get_by_id=lambda _: SimpleNamespace(id=1, exp_root_path=tmp)))
            service._file_timestamp = lambda _: datetime(2026, 10, 28, 1, 2, 3, tzinfo=timezone.utc)
            first = service.import_exps(1, ["one"], model_frameworks={"one": "hgnetv2b3"})[0]
            self.assertEqual(first["model_framework"], "hgnetv2b3")
            self.assertEqual(first["version"], "20261028090203")
            approved = service.approve_exp(first["id"], version=first["version"], description=None)
            self.assertEqual(approved["version"], first["version"])
            with self.assertRaises(ExpConflictError):
                service.import_exps(1, ["two"])
            missing = service.import_exps(1, ["missing"])[0]
            self.assertIsNone(missing["version"])

    def test_reject_retains_import_version(self):
        exp = SimpleNamespace(id=1, project_id=1, name="one", relative_path="one", resolved_path=".",
            review_status="pending_review", version="20261028090203", description=None, review_comment=None,
            imported_at=datetime.now(timezone.utc), reviewed_at=None, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
        repo = SimpleNamespace(get_by_id=lambda _: exp, add=lambda value: value, commit=lambda: None)
        result = ExpService(exp_repository=repo, project_repository=None).reject_exp(1, review_comment="retry")
        self.assertEqual(result["version"], "20261028090203")


if __name__ == "__main__":
    unittest.main()
