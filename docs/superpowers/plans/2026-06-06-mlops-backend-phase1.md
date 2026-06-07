# MLOps Backend Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable FastAPI backend skeleton for MLOps phase 1 with unified REST responses, SQLite models, YAML template loading, ClearML adapter boundaries, and scheduler wiring.

**Architecture:** Use a modular monolith under `backend/` with interface, application, domain, infrastructure, and bootstrap layers. Persist phase-1 state with unified `tasks` and `task_artifacts` tables, expose training/conversion/system APIs, and keep ClearML and scheduler behavior behind service and adapter interfaces.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, APScheduler, httpx, PyYAML, pytest

---

### Task 1: Scaffold project structure and dependency metadata

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/config/app.yaml`
- Create: `backend/config/training-templates.yaml`
- Create: `backend/config/conversion-templates.yaml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/bootstrap/__init__.py`
- Create: `backend/app/bootstrap/container.py`
- Create: `backend/app/bootstrap/lifespan.py`
- Create: `backend/tests/__init__.py`

- [ ] **Step 1: Write the failing smoke test for application import**

```python
# backend/tests/test_app_import.py
from app.main import create_app


def test_create_app_builds_fastapi_instance():
    app = create_app()
    assert app.title == "mlops-backend"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest backend/tests/test_app_import.py -q`
Expected: FAIL with import error because `app.main` does not exist yet.

- [ ] **Step 3: Write minimal project metadata and app factory**

```toml
# backend/pyproject.toml
[project]
name = "mlops-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi",
  "uvicorn",
  "pydantic>=2",
  "pydantic-settings",
  "sqlalchemy>=2",
  "alembic",
  "apscheduler",
  "httpx",
  "pyyaml",
]

[project.optional-dependencies]
dev = ["pytest"]
```

```python
# backend/app/main.py
from fastapi import FastAPI


def create_app() -> FastAPI:
    return FastAPI(title="mlops-backend")


app = create_app()
```

```yaml
# backend/config/app.yaml
app:
  name: "mlops-backend"
  env: "dev"
  debug: true
  host: "0.0.0.0"
  port: 18087
  root_path: "/api"
  docs_url: "/docs"
  openapi_url: "/openapi.json"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest backend/tests/test_app_import.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/.env.example backend/config backend/app backend/tests
git commit -m "feat: scaffold backend project skeleton"
```

### Task 2: Build configuration, logging, and unified REST response foundations

**Files:**
- Create: `backend/app/api/schemas/common.py`
- Create: `backend/app/api/errors/http.py`
- Create: `backend/app/api/deps/request_context.py`
- Create: `backend/app/infrastructure/config/__init__.py`
- Create: `backend/app/infrastructure/config/settings.py`
- Create: `backend/app/infrastructure/config/loader.py`
- Create: `backend/app/infrastructure/logging/__init__.py`
- Create: `backend/app/infrastructure/logging/setup.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/bootstrap/container.py`

- [ ] **Step 1: Write the failing test for unified response envelope**

```python
# backend/tests/test_response_schema.py
from app.api.schemas.common import ResponseEnvelope


def test_response_envelope_defaults():
    payload = ResponseEnvelope(data={"ok": True})
    assert payload.code == "OK"
    assert payload.message == "success"
    assert payload.warnings == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest backend/tests/test_response_schema.py -q`
Expected: FAIL because common response schema is missing.

- [ ] **Step 3: Implement settings loader and common response schema**

```python
# backend/app/api/schemas/common.py
from typing import Any

from pydantic import BaseModel, Field


class ResponseEnvelope(BaseModel):
    code: str = "OK"
    message: str = "success"
    data: Any = None
    request_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
```

```python
# backend/app/infrastructure/config/settings.py
from pydantic import BaseModel


class AppSettings(BaseModel):
    name: str
    env: str
    debug: bool
    host: str
    port: int
    root_path: str
    docs_url: str
    openapi_url: str
```

```python
# backend/app/infrastructure/config/loader.py
from pathlib import Path
import yaml

from .settings import AppSettings


def load_app_settings(config_path: Path) -> AppSettings:
    content = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return AppSettings(**content["app"])
```

- [ ] **Step 4: Wire the app factory to loaded settings**

```python
# backend/app/main.py
from pathlib import Path

from fastapi import FastAPI

from app.infrastructure.config.loader import load_app_settings


def create_app() -> FastAPI:
    settings = load_app_settings(Path("backend/config/app.yaml"))
    return FastAPI(
        title=settings.name,
        debug=settings.debug,
        root_path=settings.root_path,
        docs_url=settings.docs_url,
        openapi_url=settings.openapi_url,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest backend/tests/test_app_import.py backend/tests/test_response_schema.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api backend/app/infrastructure/config backend/app/infrastructure/logging backend/app/main.py backend/tests
git commit -m "feat: add settings loader and unified api response schema"
```

### Task 3: Add SQLAlchemy base models, session management, and repositories

**Files:**
- Create: `backend/app/infrastructure/db/__init__.py`
- Create: `backend/app/infrastructure/db/base.py`
- Create: `backend/app/infrastructure/db/session.py`
- Create: `backend/app/infrastructure/db/models.py`
- Create: `backend/app/infrastructure/repositories/__init__.py`
- Create: `backend/app/infrastructure/repositories/task_repository.py`
- Create: `backend/app/infrastructure/repositories/task_artifact_repository.py`
- Create: `backend/app/infrastructure/repositories/sync_checkpoint_repository.py`
- Create: `backend/app/infrastructure/repositories/job_run_repository.py`
- Create: `backend/tests/test_task_models.py`

- [ ] **Step 1: Write the failing test for task ORM defaults**

```python
# backend/tests/test_task_models.py
from app.infrastructure.db.models import TaskModel


def test_task_model_defaults():
    model = TaskModel(
        task_name="demo",
        task_group="training",
        task_type="training",
        task_source="platform",
        status="queued",
        sync_version=1,
    )
    assert model.task_group == "training"
    assert model.status == "queued"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest backend/tests/test_task_models.py -q`
Expected: FAIL because ORM model is missing.

- [ ] **Step 3: Implement base, engine, and phase-1 ORM models**

```python
# backend/app/infrastructure/db/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

```python
# backend/app/infrastructure/db/models.py
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_task_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    task_source: Mapped[str] = mapped_column(String(32))
    clearml_task_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    task_name: Mapped[str] = mapped_column(String(255))
    task_group: Mapped[str] = mapped_column(String(32), index=True)
    task_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    queue_name: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    template_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    params_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    parameter_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    runtime_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

```python
# backend/app/infrastructure/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def build_session_factory(database_url: str) -> sessionmaker:
    engine = create_engine(database_url, future=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
```

- [ ] **Step 4: Add repository interfaces for tasks and sync records**

```python
# backend/app/infrastructure/repositories/task_repository.py
from sqlalchemy.orm import Session

from app.infrastructure.db.models import TaskModel


class TaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, task: TaskModel) -> TaskModel:
        self.session.add(task)
        self.session.flush()
        return task
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest backend/tests/test_task_models.py backend/tests/test_app_import.py backend/tests/test_response_schema.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/infrastructure/db backend/app/infrastructure/repositories backend/tests/test_task_models.py
git commit -m "feat: add phase1 database models and repositories"
```

### Task 4: Introduce template service and ClearML adapter boundaries

**Files:**
- Create: `backend/app/domain/common/enums.py`
- Create: `backend/app/domain/common/exceptions.py`
- Create: `backend/app/application/dto/training.py`
- Create: `backend/app/application/services/template_service.py`
- Create: `backend/app/infrastructure/template/renderer.py`
- Create: `backend/app/infrastructure/template/validator.py`
- Create: `backend/app/infrastructure/clearml/__init__.py`
- Create: `backend/app/infrastructure/clearml/adapter.py`
- Create: `backend/app/infrastructure/clearml/clients.py`
- Create: `backend/app/infrastructure/clearml/mapper.py`
- Create: `backend/app/infrastructure/clearml/queue_probe.py`
- Create: `backend/tests/test_template_service.py`

- [ ] **Step 1: Write the failing test for YAML template loading**

```python
# backend/tests/test_template_service.py
from pathlib import Path

from app.application.services.template_service import TemplateService


def test_template_service_loads_training_template():
    service = TemplateService(Path("backend/config/training-templates.yaml"))
    template = service.get_template("yolo-default")
    assert template["name"] == "yolo-default"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest backend/tests/test_template_service.py -q`
Expected: FAIL because template service does not exist.

- [ ] **Step 3: Implement template loading and minimal rendering**

```python
# backend/app/application/services/template_service.py
from pathlib import Path
import yaml


class TemplateService:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def get_template(self, name: str) -> dict:
        content = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        for item in content["templates"]:
            if item["name"] == name:
                return item
        raise KeyError(name)
```

```yaml
# backend/config/training-templates.yaml
templates:
  - name: "yolo-default"
    task_type: "training"
    default_queue: "queue_train_gpu"
    runtime:
      python: "3.12"
    execution:
      workdir: "/workspace/train"
      entrypoint: "python train.py"
    defaults:
      epochs: 100
      imgsz: 640
```

- [ ] **Step 4: Add ClearML adapter interface and queue probe contract**

```python
# backend/app/infrastructure/clearml/adapter.py
from typing import Protocol


class ClearMLAdapter(Protocol):
    def create_task(self, payload: dict) -> dict: ...
    def list_queues(self) -> list[dict]: ...
    def list_agents(self) -> list[dict]: ...
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest backend/tests/test_template_service.py backend/tests/test_task_models.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/domain backend/app/application/dto backend/app/application/services/template_service.py backend/app/infrastructure/template backend/app/infrastructure/clearml backend/config/training-templates.yaml backend/config/conversion-templates.yaml backend/tests/test_template_service.py
git commit -m "feat: add template service and clearml adapter contracts"
```

### Task 5: Implement application services for training, conversion, and task query

**Files:**
- Create: `backend/app/application/services/task_query_service.py`
- Create: `backend/app/application/services/training_command_service.py`
- Create: `backend/app/application/services/conversion_command_service.py`
- Create: `backend/tests/test_training_command_service.py`

- [ ] **Step 1: Write the failing test for training task creation warning behavior**

```python
# backend/tests/test_training_command_service.py
from types import SimpleNamespace

from app.application.services.training_command_service import TrainingCommandService


class FakeAdapter:
    def create_task(self, payload: dict) -> dict:
        return {"id": "clearml-1", "url": "http://clearml/tasks/1"}

    def list_queues(self) -> list[dict]:
        return [{"name": "queue_train_gpu"}]

    def list_agents(self) -> list[dict]:
        return []


def test_create_training_task_returns_warning_when_no_agent_online():
    service = TrainingCommandService(
        adapter=FakeAdapter(),
        template_service=SimpleNamespace(get_template=lambda _: {"name": "yolo-default", "default_queue": "queue_train_gpu"}),
        task_repository=SimpleNamespace(add=lambda task: task),
    )
    result = service.create_task({"template_name": "yolo-default"})
    assert result["warnings"] == ["target queue has no online agent; task will wait until an agent is available"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest backend/tests/test_training_command_service.py -q`
Expected: FAIL because command service is missing.

- [ ] **Step 3: Implement training and conversion command services**

```python
# backend/app/application/services/training_command_service.py
class TrainingCommandService:
    def __init__(self, adapter, template_service, task_repository) -> None:
        self.adapter = adapter
        self.template_service = template_service
        self.task_repository = task_repository

    def create_task(self, payload: dict) -> dict:
        template = self.template_service.get_template(payload["template_name"])
        warnings: list[str] = []
        if not self.adapter.list_agents():
            warnings.append("target queue has no online agent; task will wait until an agent is available")
        created = self.adapter.create_task(payload)
        return {"task": created, "warnings": warnings, "template": template["name"]}
```

```python
# backend/app/application/services/conversion_command_service.py
class ConversionCommandService:
    def __init__(self, adapter, task_repository) -> None:
        self.adapter = adapter
        self.task_repository = task_repository

    def create_onnx_export(self, parent_task_id: int, payload: dict) -> dict:
        created = self.adapter.create_task(payload)
        return {"parent_task_id": parent_task_id, "task": created}
```

- [ ] **Step 4: Add task query service for list/detail composition**

```python
# backend/app/application/services/task_query_service.py
class TaskQueryService:
    def __init__(self, task_repository) -> None:
        self.task_repository = task_repository

    def list_tasks(self, filters: dict) -> dict:
        return self.task_repository.list_paginated(filters)

    def get_task(self, task_id: int):
        return self.task_repository.get_by_id(task_id)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest backend/tests/test_training_command_service.py backend/tests/test_template_service.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/application/services backend/tests/test_training_command_service.py
git commit -m "feat: add training conversion and query services"
```

### Task 6: Expose REST routers with unified response envelopes

**Files:**
- Create: `backend/app/api/routers/__init__.py`
- Create: `backend/app/api/routers/training.py`
- Create: `backend/app/api/routers/conversion.py`
- Create: `backend/app/api/routers/system.py`
- Create: `backend/app/api/schemas/training.py`
- Create: `backend/app/api/schemas/conversion.py`
- Create: `backend/app/api/schemas/system.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_training_router.py`

- [ ] **Step 1: Write the failing API test for unified list response**

```python
# backend/tests/test_training_router.py
from fastapi.testclient import TestClient

from app.main import create_app


def test_training_list_uses_unified_response_envelope():
    client = TestClient(create_app())
    response = client.get("/training")
    body = response.json()
    assert response.status_code == 200
    assert set(body.keys()) == {"code", "message", "data", "request_id", "warnings"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest backend/tests/test_training_router.py -q`
Expected: FAIL with 404 because router is not registered.

- [ ] **Step 3: Implement routers and request/response schemas**

```python
# backend/app/api/routers/training.py
from fastapi import APIRouter

from app.api.schemas.common import ResponseEnvelope

router = APIRouter(prefix="/training", tags=["training"])


@router.get("", response_model=ResponseEnvelope)
def list_training_tasks() -> ResponseEnvelope:
    return ResponseEnvelope(data={"items": [], "total": 0, "page": 1, "page_size": 20})
```

```python
# backend/app/api/routers/system.py
from fastapi import APIRouter

from app.api.schemas.common import ResponseEnvelope

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health", response_model=ResponseEnvelope)
def health() -> ResponseEnvelope:
    return ResponseEnvelope(data={"status": "ok"})
```

```python
# backend/app/main.py
from app.api.routers import conversion, system, training


def create_app() -> FastAPI:
    ...
    app.include_router(training.router)
    app.include_router(conversion.router)
    app.include_router(system.router)
    return app
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest backend/tests/test_training_router.py backend/tests/test_response_schema.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api backend/app/main.py backend/tests/test_training_router.py
git commit -m "feat: expose phase1 rest routers with unified envelopes"
```

### Task 7: Add scheduler bootstrap, runtime endpoints, and Alembic wiring

**Files:**
- Create: `backend/app/infrastructure/scheduler/__init__.py`
- Create: `backend/app/infrastructure/scheduler/manager.py`
- Create: `backend/app/infrastructure/scheduler/jobs.py`
- Create: `backend/app/application/services/scheduler_service.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/tests/test_system_router.py`
- Modify: `backend/app/bootstrap/lifespan.py`
- Modify: `backend/app/api/routers/system.py`

- [ ] **Step 1: Write the failing test for runtime endpoint**

```python
# backend/tests/test_system_router.py
from fastapi.testclient import TestClient

from app.main import create_app


def test_system_runtime_endpoint_exists():
    client = TestClient(create_app())
    response = client.get("/system/runtime")
    assert response.status_code == 200
    assert response.json()["data"]["scheduler"]["enabled"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest backend/tests/test_system_router.py -q`
Expected: FAIL with 404 because runtime route is missing.

- [ ] **Step 3: Implement scheduler manager and lifespan hook**

```python
# backend/app/infrastructure/scheduler/manager.py
from apscheduler.schedulers.background import BackgroundScheduler


class SchedulerManager:
    def __init__(self, timezone: str = "Asia/Shanghai") -> None:
        self.scheduler = BackgroundScheduler(timezone=timezone)

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
```

```python
# backend/app/bootstrap/lifespan.py
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app):
    scheduler = app.state.scheduler
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()
```

- [ ] **Step 4: Expose runtime endpoint and Alembic bootstrap files**

```python
# backend/app/api/routers/system.py
@router.get("/runtime", response_model=ResponseEnvelope)
def runtime() -> ResponseEnvelope:
    return ResponseEnvelope(data={"scheduler": {"enabled": True, "running": True}})
```

```python
# backend/migrations/env.py
from app.infrastructure.db.base import Base
from app.infrastructure.db import models

target_metadata = Base.metadata
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest backend/tests/test_system_router.py backend/tests/test_training_router.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/infrastructure/scheduler backend/app/application/services/scheduler_service.py backend/app/bootstrap/lifespan.py backend/alembic.ini backend/migrations backend/tests/test_system_router.py
git commit -m "feat: wire scheduler runtime endpoints and alembic bootstrap"
```

### Task 8: Final verification and developer ergonomics

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/tests/test_health_smoke.py`
- Create: `backend/README.md`

- [ ] **Step 1: Write the failing smoke test for health endpoint**

```python
# backend/tests/test_health_smoke.py
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_reports_ok():
    client = TestClient(create_app())
    response = client.get("/system/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"
```

- [ ] **Step 2: Run test to verify behavior before final cleanup**

Run: `python3 -m pytest backend/tests/test_health_smoke.py -q`
Expected: PASS or FAIL only if health route was regressed.

- [ ] **Step 3: Add dev instructions and pytest script**

```toml
# backend/pyproject.toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

```md
# backend/README.md
## Development

- Install dependencies in `.venv`
- Run `python3 -m pytest backend/tests -q`
- Start app with `uvicorn app.main:app --reload --app-dir backend`
```

- [ ] **Step 4: Run full verification**

Run: `python3 -m pytest backend/tests -q`
Expected: PASS

Run: `python3 -m compileall backend/app`
Expected: PASS without syntax errors

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/tests/test_health_smoke.py backend/README.md
git commit -m "chore: add verification and developer docs"
```
