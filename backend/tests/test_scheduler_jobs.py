from app.infrastructure.scheduler.jobs import register_scheduler_jobs
from app.infrastructure.scheduler.manager import SchedulerManager


def test_register_scheduler_jobs_uses_configured_task_status_sync_interval():
    manager = SchedulerManager(enabled=True, timezone="UTC")

    register_scheduler_jobs(
        manager,
        lambda: None,
        task_status_sync_interval_seconds=12,
    )

    jobs = manager._scheduler.get_jobs()  # type: ignore[attr-defined]
    task_sync_job = next(job for job in jobs if job.id == "task-status-sync")

    assert int(task_sync_job.trigger.interval.total_seconds()) == 12
