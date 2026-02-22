from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class Subsystem(str, Enum):
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    SYSCALL = "syscall"


class TestKind(str, Enum):
    LOAD = "load"
    STRESS = "stress"
    STABILITY = "stability"
    SCALABILITY = "scalability"
    VOLUME = "volume"
    ISOLATED = "isolated"
    SPIKE = "spike"


class LoadPattern(str, Enum):
    SOFT = "soft"
    BALANCED = "balanced"
    INTENSE = "intense"
    EXTREME = "extreme"
    SPIKE = "spike"


@dataclass(frozen=True)
class LoadTask:
    subsystem: Subsystem
    tool: str
    args: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "subsystem": self.subsystem.value,
            "tool": self.tool,
            "args": self.args,
        }


@dataclass(frozen=True)
class PlanStage:
    name: str
    start_offset_sec: int
    duration_sec: int
    pattern: LoadPattern
    tasks: tuple[LoadTask, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "start_offset_sec": self.start_offset_sec,
            "duration_sec": self.duration_sec,
            "pattern": self.pattern.value,
            "tasks": [task.to_dict() for task in self.tasks],
        }


@dataclass(frozen=True)
class PlanRequest:
    duration_sec: int
    subsystems: tuple[Subsystem, ...]
    test_kind: TestKind
    pattern: LoadPattern | None = None


@dataclass(frozen=True)
class TestPlan:
    plan_id: str
    created_at: datetime
    duration_sec: int
    subsystems: tuple[Subsystem, ...]
    test_kind: TestKind
    stages: tuple[PlanStage, ...]

    @staticmethod
    def new(
        duration_sec: int,
        subsystems: tuple[Subsystem, ...],
        test_kind: TestKind,
        stages: tuple[PlanStage, ...],
    ) -> TestPlan:
        return TestPlan(
            plan_id=uuid4().hex[:10],
            created_at=datetime.now(UTC),
            duration_sec=duration_sec,
            subsystems=subsystems,
            test_kind=test_kind,
            stages=stages,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "created_at": self.created_at.isoformat(),
            "duration_sec": self.duration_sec,
            "subsystems": [x.value for x in self.subsystems],
            "test_kind": self.test_kind.value,
            "stages": [stage.to_dict() for stage in self.stages],
        }
