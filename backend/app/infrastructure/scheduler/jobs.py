from typing import Callable

from app.infrastructure.scheduler.manager import SchedulerManager


def _scheduler_heartbeat() -> None:
    return None


def register_scheduler_jobs(
    manager: SchedulerManager,
    sync_task_statuses_job: Callable[[], None],
    *,
    task_status_sync_interval_seconds: int,
) -> None:
    manager.add_interval_job(
        _scheduler_heartbeat,
        job_id="scheduler-heartbeat",
        seconds=3600,
    )
    manager.add_interval_job(
        sync_task_statuses_job,
        job_id="task-status-sync",
        seconds=task_status_sync_interval_seconds,
    )
