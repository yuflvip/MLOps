try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal test env
    class BackgroundScheduler:  # type: ignore[no-redef]
        def __init__(self, timezone: str = "UTC") -> None:
            self.timezone = timezone
            self.running = False
            self._jobs = []

        def add_job(
            self,
            func,
            trigger: str,
            seconds: int,
            id: str,
            replace_existing: bool = True,
        ) -> None:
            if replace_existing:
                self._jobs = [job for job in self._jobs if job["id"] != id]
            self._jobs.append(
                {
                    "id": id,
                    "func": func,
                    "trigger": trigger,
                    "seconds": seconds,
                }
            )

        def get_jobs(self):
            return list(self._jobs)

        def start(self) -> None:
            self.running = True

        def shutdown(self, wait: bool = False) -> None:
            self.running = False


class SchedulerManager:
    def __init__(self, enabled: bool = True, timezone: str = "UTC") -> None:
        self._enabled = enabled
        self._scheduler = (
            BackgroundScheduler(timezone=timezone) if enabled else None
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def running(self) -> bool:
        return bool(self._scheduler and self._scheduler.running)

    @property
    def job_count(self) -> int:
        if not self._scheduler:
            return 0
        return len(self._scheduler.get_jobs())

    def add_interval_job(
        self,
        func,
        *,
        job_id: str,
        seconds: int,
    ) -> None:
        if not self._scheduler:
            return
        self._scheduler.add_job(
            func,
            trigger="interval",
            seconds=seconds,
            id=job_id,
            replace_existing=True,
        )

    def start(self) -> None:
        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()

    def shutdown(self) -> None:
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def get_status(self) -> dict:
        return {
            "enabled": self.enabled,
            "running": self.running,
            "job_count": self.job_count,
        }
