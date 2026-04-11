from __future__ import annotations

from collections.abc import Callable
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.platform.manifest import AgentManifest


class SchedulerKernel:
    def __init__(self, scheduler: AsyncIOScheduler | None = None):
        self.scheduler = scheduler or AsyncIOScheduler()

    def add_agent_job(
        self,
        agent_key: str,
        job_name: str,
        func: Callable[..., Any],
        trigger: str,
        **kwargs: Any,
    ) -> None:
        job_id = f"{agent_key}:{job_name}"
        self.scheduler.add_job(func, trigger, id=job_id, replace_existing=True, **kwargs)

    def register_agent(self, manifest: AgentManifest) -> None:
        if manifest.job_registrar is not None:
            manifest.job_registrar(self)

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown()
