from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter

if TYPE_CHECKING:
    from app.platform.scheduler import SchedulerKernel


JobRegistrar = Callable[["SchedulerKernel"], None]


@dataclass(slots=True)
class AgentManifest:
    key: str
    name: str
    description: str
    router: APIRouter | None = None
    job_registrar: JobRegistrar | None = None
    builtin_skills: list[dict[str, Any]] = field(default_factory=list)
