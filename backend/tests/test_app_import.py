from pathlib import Path

from app.main import create_app


def test_create_app_builds_fastapi_instance():
    app = create_app()
    assert app.title == "mlops-backend"


def test_backend_uses_app_as_only_source_package():
    backend_dir = Path(__file__).resolve().parents[1]
    assert (backend_dir / "app").is_dir()
    assert not (backend_dir / "mlops_backend").exists()
