import os
from pathlib import Path
from typing import Optional, Union

import yaml

from app.infrastructure.config.settings import Settings

CONFIG_PATH_ENV_VAR = "MLOPS_BACKEND_CONFIG_PATH"


class ConfigError(RuntimeError):
    """Base class for configuration loading failures."""


class ConfigFileNotFoundError(ConfigError):
    """Raised when the configured settings file does not exist."""


class ConfigFileParseError(ConfigError):
    """Raised when the settings file cannot be parsed."""


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / "app.yaml"


def resolve_config_path(config_path: Optional[Union[Path, str]] = None) -> Path:
    candidate = config_path or os.getenv(CONFIG_PATH_ENV_VAR) or default_config_path()
    return Path(candidate).expanduser().resolve()


def load_settings(config_path: Optional[Union[Path, str]] = None) -> Settings:
    path = resolve_config_path(config_path)
    if not path.exists():
        raise ConfigFileNotFoundError("Configuration file does not exist: %s" % path)

    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigFileParseError("Failed to parse configuration file: %s" % path) from exc

    return Settings.model_validate(content)
