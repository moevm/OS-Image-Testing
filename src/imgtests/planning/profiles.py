from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from imgtests.planning.models import LoadPattern, LoadTask, TestKind
from imgtests.types import Subsystem


@dataclass(frozen=True)
class StageTemplate:
    name: str
    pattern: LoadPattern
    weight: float


PROFILE_LAYOUTS: dict[TestKind, tuple[StageTemplate, ...]] = {
    TestKind.LOAD: (
        StageTemplate("warmup", LoadPattern.SOFT, 0.20),
        StageTemplate("main", LoadPattern.BALANCED, 0.60),
        StageTemplate("cooldown", LoadPattern.SOFT, 0.20),
    ),
    TestKind.STRESS: (
        StageTemplate("ramp", LoadPattern.BALANCED, 0.15),
        StageTemplate("peak", LoadPattern.EXTREME, 0.70),
        StageTemplate("cooldown", LoadPattern.INTENSE, 0.15),
    ),
    TestKind.STABILITY: (StageTemplate("soak", LoadPattern.BALANCED, 1.00),),
    TestKind.SCALABILITY: (
        StageTemplate("step_soft", LoadPattern.SOFT, 0.25),
        StageTemplate("step_balanced", LoadPattern.BALANCED, 0.25),
        StageTemplate("step_intense", LoadPattern.INTENSE, 0.25),
        StageTemplate("step_extreme", LoadPattern.EXTREME, 0.25),
    ),
    TestKind.VOLUME: (
        StageTemplate("prefill", LoadPattern.BALANCED, 0.25),
        StageTemplate("bulk", LoadPattern.INTENSE, 0.75),
    ),
    TestKind.SPIKE: (
        StageTemplate("baseline_1", LoadPattern.SOFT, 0.45),
        StageTemplate("spike", LoadPattern.SPIKE, 0.10),
        StageTemplate("baseline_2", LoadPattern.SOFT, 0.45),
    ),
    TestKind.ISOLATED: (StageTemplate("tools_smoke", LoadPattern.SOFT, 1.00),),
}

_STRESS_ARGS: dict[Subsystem, dict[LoadPattern, dict[str, Any]]] = {
    Subsystem.SYSTEM: {
        LoadPattern.SOFT: {"cpu": 1, "cpu_method": "matrixprod"},
        LoadPattern.BALANCED: {"cpu": 0, "cpu_method": "all"},
        LoadPattern.INTENSE: {"cpu": 0, "cpu_method": "all"},
        LoadPattern.EXTREME: {"cpu": 0, "cpu_method": "all"},
        LoadPattern.SPIKE: {"cpu": 0, "cpu_method": "all"},
    },
    Subsystem.IPC: {
        LoadPattern.SOFT: {"mq": 1, "pipe": 1, "sem": 1, "shm": 1},
        LoadPattern.BALANCED: {"mq": 2, "pipe": 2, "sem": 2, "shm": 2},
        LoadPattern.INTENSE: {"mq": 4, "pipe": 4, "sem": 4, "shm": 4},
        LoadPattern.EXTREME: {"mq": 6, "pipe": 6, "sem": 6, "shm": 6},
        LoadPattern.SPIKE: {"mq": 8, "pipe": 8, "sem": 8, "shm": 8},
    },
    Subsystem.MEMORY: {
        LoadPattern.SOFT: {"vm": 1, "vm_method": "all", "vm_bytes": "10%"},
        LoadPattern.BALANCED: {"vm": 2, "vm_method": "all", "vm_bytes": "20%"},
        LoadPattern.INTENSE: {"vm": 4, "vm_method": "all", "vm_bytes": "35%"},
        LoadPattern.EXTREME: {
            "vm": 8,
            "vm_method": "all",
            "vm_bytes": "50%",
            "vm-populate": True,
        },
        LoadPattern.SPIKE: {
            "vm": 8,
            "vm_method": "all",
            "vm_bytes": "55%",
            "vm-populate": True,
        },
    },
    Subsystem.NETWORK: {
        LoadPattern.SOFT: {"sock": 1, "sock_ops": 50_000},
        LoadPattern.BALANCED: {"sock": 2, "sock_ops": 150_000},
        LoadPattern.INTENSE: {"sock": 4, "sock_ops": 250_000},
        LoadPattern.EXTREME: {"sock": 6, "sock_ops": 350_000},
        LoadPattern.SPIKE: {"sock": 8, "sock_ops": 500_000},
    },
    Subsystem.SYSCALLS: {
        LoadPattern.SOFT: {"syscall": 1},
        LoadPattern.BALANCED: {"syscall": 2},
        LoadPattern.INTENSE: {"syscall": 4},
        LoadPattern.EXTREME: {"syscall": 6},
        LoadPattern.SPIKE: {"syscall": 8},
    },
}

_FIO_ARGS: dict[LoadPattern, dict[str, Any]] = {
    LoadPattern.SOFT: {
        "readwrite": "read",
        "bs": "128k",
        "numjobs": 1,
        "iodepth": 1,
        "size": "256M",
    },
    LoadPattern.BALANCED: {
        "readwrite": "randrw",
        "bs": "16k",
        "numjobs": 2,
        "iodepth": 4,
        "size": "512M",
    },
    LoadPattern.INTENSE: {
        "readwrite": "randrw",
        "bs": "4k",
        "numjobs": 4,
        "iodepth": 16,
        "size": "768M",
    },
    LoadPattern.EXTREME: {
        "readwrite": "randwrite",
        "bs": "4k",
        "numjobs": 6,
        "iodepth": 24,
        "size": "1G",
    },
    LoadPattern.SPIKE: {
        "readwrite": "randwrite",
        "bs": "4k",
        "numjobs": 6,
        "iodepth": 24,
        "size": "1G",
    },
}


def build_task(subsystem: Subsystem, pattern: LoadPattern, stage_duration_sec: int) -> LoadTask:
    if subsystem == Subsystem.FILE:
        args = dict(_FIO_ARGS[pattern])
        args["runtime_sec"] = stage_duration_sec
        return LoadTask(subsystem=subsystem, tool="fio", args=args)

    subsystem_args = _STRESS_ARGS.get(subsystem, {})
    args = dict(subsystem_args.get(pattern, {}))
    args["timeout_sec"] = stage_duration_sec
    return LoadTask(subsystem=subsystem, tool="stress-ng", args=args)


def build_stage_tasks(
    _test_kind: TestKind,
    subsystems: frozenset[Subsystem],
    pattern: LoadPattern,
    stage_duration_sec: int,
) -> tuple[LoadTask, ...]:
    return tuple(
        build_task(ss, pattern, stage_duration_sec)
        for ss in sorted(subsystems, key=lambda item: item.value)
    )
