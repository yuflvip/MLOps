from typing import Dict

from pydantic import BaseModel, Field, field_validator


def _normalize_path_prefix(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if text == "/":
        return "/"
    if not text.startswith("/"):
        text = f"/{text}"
    return text.rstrip("/")


class AppSettings(BaseModel):
    name: str = "mlops-backend"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 18087
    root_path: str = ""
    api_prefix: str = ""
    docs_url: str = "/docs"
    openapi_url: str = "/openapi.json"

    @field_validator("root_path", "api_prefix", "docs_url", "openapi_url", mode="before")
    @classmethod
    def _normalize_paths(cls, value: object) -> str:
        return _normalize_path_prefix(value)


class LoggingSettings(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


class DatabaseSettings(BaseModel):
    url: str = "sqlite+pysqlite:///./data/mlops.db"


class TemplateSourceSettings(BaseModel):
    training: str = "./config/training-templates.yaml"
    conversion: str = "./config/conversion-templates.yaml"


class ClearMLSettings(BaseModel):
    mode: str = "stub"
    api_base_url: str = "http://127.0.0.1:8008"
    access_key: str = ""
    secret_key: str = ""
    timeout_seconds: int = 30
    runner_working_dir: str = "/home/yufl/workspace-2026/MLOps/backend/scripts"
    runner_entrypoint: str = "entrypoint.py"


class SchedulerSettings(BaseModel):
    enabled: bool = True
    timezone: str = "UTC"
    task_status_sync_interval_seconds: int = 30


class ModelConverterRuntimeSettings(BaseModel):
    enabled: bool = False
    python_path: str = ""
    working_dir: str = ""
    script_path: str = ""


class ModelConversionSettings(BaseModel):
    max_concurrency: int = Field(default=3, ge=1)
    log_dir: str = "./data/conversion-logs"
    converters: Dict[str, ModelConverterRuntimeSettings] = Field(default_factory=dict)


class QuantizationDatasetSettings(BaseModel):
    storage_root: str = "./data/quantization-datasets"
    max_image_size_mb: int = Field(default=100, ge=1)


class Settings(BaseModel):
    app: AppSettings = Field(default_factory=AppSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    templates: TemplateSourceSettings = Field(default_factory=TemplateSourceSettings)
    clearml: ClearMLSettings = Field(default_factory=ClearMLSettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    model_conversion: ModelConversionSettings = Field(default_factory=ModelConversionSettings)
    quantization_dataset: QuantizationDatasetSettings = Field(
        default_factory=QuantizationDatasetSettings
    )
