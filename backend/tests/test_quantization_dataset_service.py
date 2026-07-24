from pathlib import Path

from app.application.services import QuantizationDatasetService
from app.infrastructure.db import Base, build_session_factory
from app.infrastructure.repositories import QuantizationDatasetRepository


def _build_service(tmp_path: Path):
    session_factory = build_session_factory("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(session_factory.kw["bind"])
    session = session_factory()
    service = QuantizationDatasetService(
        QuantizationDatasetRepository(session),
        storage_root=tmp_path / "quantization",
        max_image_size_mb=1,
    )
    return service, session


def test_upload_and_delete_images_rewrites_ref_img_list(tmp_path: Path) -> None:
    service, session = _build_service(tmp_path)
    try:
        dataset = service.create_dataset(name="3403 calibration", description=None)

        first = service.upload_image(
            dataset["id"], filename="sample.jpg", content=b"first-image"
        )
        second = service.upload_image(
            dataset["id"], filename="sample.jpg", content=b"second-image"
        )

        assert first["image"]["name"] == "sample.jpg"
        assert second["image"]["name"] == "sample.jpg"
        assert second["dataset"]["image_count"] == 1
        assert (
            Path(dataset["storage_path"]) / "images" / "sample.jpg"
        ).read_bytes() == b"second-image"

        image_list_path = Path(second["dataset"]["image_list_path"])
        lines = image_list_path.read_text(encoding="utf-8").splitlines()
        assert lines == [
            str(Path(dataset["storage_path"]) / "images" / "sample.jpg"),
        ]

        updated = service.delete_images(dataset["id"], ["sample.jpg"])
        assert updated["image_count"] == 0
        assert image_list_path.read_text(encoding="utf-8") == ""
    finally:
        session.close()


def test_delete_dataset_removes_managed_directory(tmp_path: Path) -> None:
    service, session = _build_service(tmp_path)
    try:
        dataset = service.create_dataset(name="temporary", description=None)
        storage_path = Path(dataset["storage_path"])
        assert storage_path.is_dir()

        assert service.delete_dataset(dataset["id"]) is True
        assert not storage_path.exists()
    finally:
        session.close()
