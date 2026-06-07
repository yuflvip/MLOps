from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import SyncCheckpointModel


class SyncCheckpointRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, checkpoint: SyncCheckpointModel) -> SyncCheckpointModel:
        self.session.add(checkpoint)
        self.session.flush()
        self.session.refresh(checkpoint)
        return checkpoint

    def get_by_scope(self, sync_scope: str) -> Optional[SyncCheckpointModel]:
        stmt = select(SyncCheckpointModel).where(SyncCheckpointModel.sync_scope == sync_scope)
        return self.session.scalar(stmt)
