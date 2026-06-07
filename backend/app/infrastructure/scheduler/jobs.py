from app.infrastructure.scheduler.manager import SchedulerManager


def _scheduler_heartbeat() -> None:
    return None


def register_scheduler_jobs(manager: SchedulerManager) -> None:
    manager.add_interval_job(
        _scheduler_heartbeat,
        job_id="scheduler-heartbeat",
        seconds=3600,
    )
