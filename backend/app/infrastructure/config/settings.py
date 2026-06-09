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


class SchedulerSettings(BaseModel):
    enabled: bool = True
    timezone: str = "UTC"


class Settings(BaseModel):
    app: AppSettings = Field(default_factory=AppSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    templates: TemplateSourceSettings = Field(default_factory=TemplateSourceSettings)
    clearml: ClearMLSettings = Field(default_factory=ClearMLSettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
