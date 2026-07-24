from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import ModelConversionModel


ACTIVE_STATUSES = {"queued", "running"}


class ModelConversionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, conversion: ModelConversionModel) -> ModelConversionModel:
        self._session.add(conversion)
        self._session.flush()
        self._session.refresh(conversion)
        return conversion

    def commit(self) -> None:
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def get_by_id(self, conversion_id: int) -> Optional[ModelConversionModel]:
        return self._session.get(ModelConversionModel, conversion_id)

    def list_by_exp(self, exp_id: int) -> List[ModelConversionModel]:
        stmt = (
            select(ModelConversionModel)
            .where(ModelConversionModel.exp_id == exp_id)
            .order_by(ModelConversionModel.id.desc())
        )
        return list(self._session.scalars(stmt))

    def get_active_by_output(
        self, exp_id: int, output_file: str
    ) -> Optional[ModelConversionModel]:
        stmt = select(ModelConversionModel).where(
            ModelConversionModel.exp_id == exp_id,
            ModelConversionModel.output_file == output_file,
            ModelConversionModel.status.in_(ACTIVE_STATUSES),
        )
        return self._session.scalar(stmt)
