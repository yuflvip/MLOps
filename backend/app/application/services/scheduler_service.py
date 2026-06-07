from app.infrastructure.scheduler import SchedulerManager


class SchedulerService:
    def __init__(self, scheduler_manager: SchedulerManager) -> None:
        self._scheduler_manager = scheduler_manager

    def get_runtime_status(self) -> dict:
        return {"scheduler": self._scheduler_manager.get_status()}
