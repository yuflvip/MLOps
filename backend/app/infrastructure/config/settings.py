from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    name: str = "mlops-backend"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 18087
    root_path: str = ""
    docs_url: str = "/docs"
    openapi_url: str = "/openapi.json"


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
