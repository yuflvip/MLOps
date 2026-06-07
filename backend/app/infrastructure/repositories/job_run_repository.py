from typing import Optional

from sqlalchemy.orm import Session

from app.infrastructure.db.models import JobRunModel


class JobRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, job_run: JobRunModel) -> JobRunModel:
        self.session.add(job_run)
        self.session.flush()
        self.session.refresh(job_run)
        return job_run

    def get_by_id(self, job_run_id: int) -> Optional[JobRunModel]:
        return self.session.get(JobRunModel, job_run_id)
