from pydantic import BaseModel


class HealthData(BaseModel):
    status: str
    app_name: str


class SchedulerStatusData(BaseModel):
    enabled: bool
    running: bool
    job_count: int


class RuntimeData(BaseModel):
    scheduler: SchedulerStatusData
