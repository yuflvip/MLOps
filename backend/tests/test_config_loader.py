from pathlib import Path

import pytest

from app.infrastructure.config.loader import (
    ConfigFileNotFoundError,
    load_settings,
)
from app.infrastructure.config.settings import SchedulerSettings


def test_load_settings_raises_clear_error_when_config_missing(tmp_path: Path):
    missing_path = tmp_path / "missing.yaml"

    with pytest.raises(ConfigFileNotFoundError) as exc_info:
        load_settings(missing_path)

    assert str(missing_path) in str(exc_info.value)


def test_scheduler_settings_default_task_status_sync_interval_seconds():
    settings = SchedulerSettings()

    assert settings.task_status_sync_interval_seconds == 30


def test_load_settings_reads_task_status_sync_interval_seconds(tmp_path: Path):
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        """
scheduler:
  enabled: true
  timezone: "UTC"
  task_status_sync_interval_seconds: 12
""".strip(),
        encoding="utf-8",
    )

    settings = load_settings(config_path)

    assert settings.scheduler.task_status_sync_interval_seconds == 12
