from pathlib import Path

import pytest

from app.infrastructure.config.loader import (
    ConfigFileNotFoundError,
    load_settings,
)


def test_load_settings_raises_clear_error_when_config_missing(tmp_path: Path):
    missing_path = tmp_path / "missing.yaml"

    with pytest.raises(ConfigFileNotFoundError) as exc_info:
        load_settings(missing_path)

    assert str(missing_path) in str(exc_info.value)
