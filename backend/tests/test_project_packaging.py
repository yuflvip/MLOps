import unittest
from types import SimpleNamespace

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.schemas.project import ProjectPackagingConfig
from app.application.services.project_service import ProjectService
from app.infrastructure.config.settings import Settings
from app.infrastructure.db.base import Base
from app.infrastructure.repositories.project_repository import ProjectRepository


class ProjectPackagingTests(unittest.TestCase):
    def test_platform_suffixes_and_normalization(self):
        config = ProjectPackagingConfig(
            model_links={"692": "vehicle_base_classifier.bin"},
            cfg_content="[yolo]\r\nclass_num=2\r\n", names_content="car\r\nbus\r\n")
        for platform in ("x86", "692", "530", "3403svp", "3403nnn", "rk3588"):
            suffix = ".bin" if platform in {"692", "530"} else ".weights"
            self.assertEqual(config.model_links[platform], "vehicle_base_classifier" + suffix)
        self.assertNotIn("\r", config.cfg_content)
        self.assertEqual(config.names_content, "car\nbus\n")

    def test_reject_invalid_configuration(self):
        for payload in (
            {"model_links": {"692": "vehicle.weights"}},
            {"model_links": {"x86": "vehicle.bin"}},
            {"model_links": {"unknown": "vehicle.weights"}},
            {"model_links": {"x86": "one.weights", "530": "two.bin"}},
            {"cfg_filename": "../model.cfg"},
            {"names_link": "bad name.names"},
            {"cfg_content": "x" * (1048576 + 1)},
        ):
            with self.subTest(payload=str(payload)[:100]), self.assertRaises(ValidationError):
                ProjectPackagingConfig.model_validate(payload)

    def test_persistence_update_and_legacy_client(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            service = ProjectService(project_repository=ProjectRepository(session),
                dataset_repository=SimpleNamespace(get_by_id=lambda _: SimpleNamespace(task_type="classification")))
            payload = dict(project="vehicle", name="基础车型", model_type="classification",
                model_architecture="HGNetV2", description=None, exp_root_path=str(__import__('pathlib').Path.cwd()),
                dataset_ids=[1], epochs=None, batch=None, imgsz=None)
            config = dict(package_key="classify_vehiclebase", model_links={"x86": "vehicle.weights"},
                cfg_content="[yolo]\nclass_num=2", names_content="car\nbus")
            created = service.create_project(**payload, packaging=config)
            self.assertEqual(service.get_project(created["id"])["packaging"]["names_content"], "car\nbus")
            self.assertEqual(created["packaging"]["model_links"]["530"], "vehicle.bin")
            service.update_project(created["id"], **payload)
            self.assertNotIn("package_key", service.get_project(created["id"])["packaging"])
            self.assertEqual(created["packaging"]["cfg_filename"], "vehicle.cfg")
            self.assertEqual(created["packaging"]["names_filename"], "vehicle.names")
            payload["project"] = "vehicle_updated"
            renamed = service.update_project(created["id"], **payload)
            self.assertEqual(renamed["packaging"]["cfg_filename"], "vehicle_updated.cfg")
            self.assertEqual(renamed["packaging"]["names_content"], "car\nbus")
            updated = service.update_project(created["id"], **payload, packaging={})
            self.assertEqual(updated["packaging"]["model_links"], {})

    def test_global_default(self):
        self.assertEqual(Settings().model_packaging.deploy_dir, "/opt/AII/YoloModel")


if __name__ == "__main__":
    unittest.main()
