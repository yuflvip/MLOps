from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

from app.application.services.template_service import TemplateService
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


def build_container(config_path: Optional[Union[Path, str]] = None) -> ApplicationContainer:
    resolved_config_path = resolve_config_path(config_path)
    settings = load_settings(resolved_config_path)
    config_dir = resolved_config_path.parent
    session_factory = build_session_factory(
        normalize_database_url(settings.database.url, config_dir.parent)
    )
    Base.metadata.create_all(session_factory.kw["bind"])
    scheduler_manager = SchedulerManager(
        enabled=settings.scheduler.enabled,
        timezone=settings.scheduler.timezone,
    )
    register_scheduler_jobs(scheduler_manager)
    return ApplicationContainer(
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
        clearml_adapter=ClearMLAdapter(_build_clearml_client(settings)),
        scheduler_manager=scheduler_manager,
    )
def _resolve_template_path(template_path: str, config_dir: Path) -> Path:
    path = Path(template_path)
    if not path.is_absolute():
        return (config_dir.parent / path).resolve()
    return path


def _build_clearml_client(settings: Settings):
    if settings.clearml.mode == "http":
        return HttpClearMLClient(
            api_base_url=settings.clearml.api_base_url,
            access_key=settings.clearml.access_key,
            secret_key=settings.clearml.secret_key,
            timeout_seconds=settings.clearml.timeout_seconds,
        )
    return StubClearMLClient()
