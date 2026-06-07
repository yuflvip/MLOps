from typing import Optional

from sqlalchemy.orm import Session

from app.infrastructure.db.models import TaskArtifactModel


class TaskArtifactRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, artifact: TaskArtifactModel) -> TaskArtifactModel:
        self.session.add(artifact)
        self.session.flush()
        self.session.refresh(artifact)
        return artifact

    def get_by_id(self, artifact_id: int) -> Optional[TaskArtifactModel]:
        return self.session.get(TaskArtifactModel, artifact_id)
