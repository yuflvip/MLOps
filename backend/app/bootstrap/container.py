from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

from app.application.services.template_service import TemplateService
from app.application.services.task_status_sync_service import TaskStatusSyncService
from app.infrastructure.clearml import (
    ClearMLAdapter,
    HttpClearMLClient,
    StubClearMLClient,
)
from app.infrastructure.config import (
    Settings,
    load_settings,
    resolve_config_path,
)
from app.infrastructure.db import (
    Base,
    build_session_factory,
    normalize_database_url,
)
from app.infrastructure.scheduler import (
    SchedulerManager,
    register_scheduler_jobs,
)
from app.infrastructure.repositories import TaskRepository
from app.infrastructure.model_conversion import LocalModelConversionScheduler


@dataclass
class ApplicationContainer:
    config_path: Path
    config_dir: Path
    settings: Settings
    session_factory: Any
    training_template_service: TemplateService
    conversion_template_service: TemplateService
    clearml_adapter: ClearMLAdapter
    scheduler_manager: SchedulerManager
    model_conversion_scheduler: LocalModelConversionScheduler


def build_container(config_path: Optional[Union[Path, str]] = None) -> ApplicationContainer:
    resolved_config_path = resolve_config_path(config_path)
    settings = load_settings(resolved_config_path)
    config_dir = resolved_config_path.parent
    _resolve_model_converter_paths(settings, config_dir.parent)
    session_factory = build_session_factory(
        normalize_database_url(settings.database.url, config_dir.parent)
    )
    Base.metadata.create_all(session_factory.kw["bind"])
    scheduler_manager = SchedulerManager(
        enabled=settings.scheduler.enabled,
        timezone=settings.scheduler.timezone,
    )
    clearml_adapter = ClearMLAdapter(_build_clearml_client(settings))
    conversion_log_dir = Path(settings.model_conversion.log_dir)
    if not conversion_log_dir.is_absolute():
        conversion_log_dir = (config_dir.parent / conversion_log_dir).resolve()
    model_conversion_scheduler = LocalModelConversionScheduler(
        session_factory=session_factory,
        settings=settings.model_conversion,
        log_dir=conversion_log_dir,
    )
    container = ApplicationContainer(
        config_path=resolved_config_path,
        config_dir=config_dir,
        settings=settings,
        session_factory=session_factory,
        training_template_service=TemplateService(
            _resolve_template_path(settings.templates.training, config_dir)
        ),
        conversion_template_service=TemplateService(
            _resolve_template_path(settings.templates.conversion, config_dir)
        ),
        clearml_adapter=clearml_adapter,
        scheduler_manager=scheduler_manager,
        model_conversion_scheduler=model_conversion_scheduler,
    )
    register_scheduler_jobs(
        scheduler_manager,
        _build_task_status_sync_job(container),
        task_status_sync_interval_seconds=(
            settings.scheduler.task_status_sync_interval_seconds
        ),
    )
    return container


def _resolve_template_path(template_path: str, config_dir: Path) -> Path:
    path = Path(template_path)
    if not path.is_absolute():
        return (config_dir.parent / path).resolve()
    return path


def _resolve_model_converter_paths(settings: Settings, backend_dir: Path) -> None:
    for runtime in settings.model_conversion.converters.values():
        for field_name in ("working_dir", "script_path"):
            raw_value = getattr(runtime, field_name)
            if not raw_value:
                continue
            path = Path(raw_value)
            if not path.is_absolute():
                setattr(runtime, field_name, str((backend_dir / path).resolve()))


def _build_clearml_client(settings: Settings):
    if settings.clearml.mode == "http":
        return HttpClearMLClient(
            api_base_url=settings.clearml.api_base_url,
            access_key=settings.clearml.access_key,
            secret_key=settings.clearml.secret_key,
            timeout_seconds=settings.clearml.timeout_seconds,
            runner_working_dir=settings.clearml.runner_working_dir,
            runner_entrypoint=settings.clearml.runner_entrypoint,
        )
    return StubClearMLClient()


def _build_task_status_sync_job(container: ApplicationContainer):
    def run() -> None:
        session = container.session_factory()
        try:
            repository = TaskRepository(session)
            service = TaskStatusSyncService(
                clearml_adapter=container.clearml_adapter,
                task_repository=repository,
            )
            service.sync_pending_tasks(limit=100)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return run
