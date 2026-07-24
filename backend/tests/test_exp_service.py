from types import SimpleNamespace

import pytest

from app.application.services.exp_service import ExpService
from app.domain.common.exceptions import ExpConflictError


class FakeExpRepository:
    def __init__(self, exp):
        self.exp = exp
        self.deleted = None
        self.committed = False

    def get_by_id(self, exp_id: int):
        if self.exp is not None and self.exp.id == exp_id:
            return self.exp
        return None

    def delete(self, exp) -> None:
        self.deleted = exp

    def commit(self) -> None:
        self.committed = True


@pytest.mark.parametrize("review_status", ["pending_review", "rejected"])
def test_delete_exp_allows_exp_that_is_not_approved(review_status: str):
    exp = SimpleNamespace(id=7, review_status=review_status)
    repository = FakeExpRepository(exp)
    service = ExpService(exp_repository=repository, project_repository=SimpleNamespace())

    assert service.delete_exp(7) is True
    assert repository.deleted is exp
    assert repository.committed is True


def test_delete_exp_rejects_approved_exp():
    exp = SimpleNamespace(id=7, review_status="approved")
    repository = FakeExpRepository(exp)
    service = ExpService(exp_repository=repository, project_repository=SimpleNamespace())

    with pytest.raises(ExpConflictError, match="cannot be deleted"):
        service.delete_exp(7)

    assert repository.deleted is None
    assert repository.committed is False
