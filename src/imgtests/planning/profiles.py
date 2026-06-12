"""Profile definitions for image testing.

This module provides profile layouts, task builders, and configuration for
various test kinds (load, stress, stability, scalability, volume, spike,
isolated, and diagnostic tests) using different subsystems (file, IPC, memory,
network, syscalls, system).

Public functions:
    - build_task: Build a LoadTask for a given subsystem, pattern, and duration.
    - build_stage_tasks: Build a tuple of LoadTasks for a stage based on test kind.

Example:
    To build a task for memory subsystem with balanced pattern:

    >>> from imgtests.planning.profiles import build_task
    >>> from imgtests.types import Subsystem
    >>> from imgtests.planning.models import LoadPattern
    >>> task = build_task(Subsystem.MEMORY, LoadPattern.BALANCED, 60)
    >>> task.tool
    'stress-ng'
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from imgtests.planning.models import LoadPattern, LoadTask, TestKind
from imgtests.types import Subsystem

CPU_SCALE_ARG_PREFIX: Final = "@cpu:"
FIO_SIZE_RATIO_ARG_PREFIX: Final = "@avail_ratio:"


@dataclass(frozen=True)
class StageTemplate:
    """Template for a test stage.

    Args:
        name: The name of the stage.
        pattern: The load pattern for the stage.
        weight: The weight of the stage relative to other stages.
    """

    name: str
    pattern: LoadPattern
    weight: float


_CPU_INSTANCE_SCALES: dict[LoadPattern, float] = {
    LoadPattern.SOFT: 0.25,
    LoadPattern.BALANCED: 0.5,
    LoadPattern.INTENSE: 1.0,
    LoadPattern.EXTREME: 1.5,
    LoadPattern.SPIKE: 2.0,
}

_VM_BYTES: dict[LoadPattern, str] = {
    LoadPattern.SOFT: "10%",
    LoadPattern.BALANCED: "20%",
    LoadPattern.INTENSE: "35%",
    LoadPattern.EXTREME: "50%",
    LoadPattern.SPIKE: "55%",
}

_VM_POPULATE_PATTERNS = frozenset({LoadPattern.EXTREME, LoadPattern.SPIKE})

_SOCK_OPS: dict[LoadPattern, int] = {
    LoadPattern.SOFT: 50_000,
    LoadPattern.BALANCED: 150_000,
    LoadPattern.INTENSE: 250_000,
    LoadPattern.EXTREME: 350_000,
    LoadPattern.SPIKE: 500_000,
}

_FIO_SIZE_RATIOS: dict[LoadPattern, float] = {
    LoadPattern.SOFT: 0.025,
    LoadPattern.BALANCED: 0.05,
    LoadPattern.INTENSE: 0.075,
    LoadPattern.EXTREME: 0.1,
    LoadPattern.SPIKE: 0.1,
}


def _cpu_scaled_arg(pattern: LoadPattern) -> str:
    """Generate CPU scaling argument for a load pattern."""
    return f"{CPU_SCALE_ARG_PREFIX}{_CPU_INSTANCE_SCALES[pattern]}"


def _avail_ratio_arg(pattern: LoadPattern) -> str:
    """Generate FIO size ratio argument for a load pattern."""
    return f"{FIO_SIZE_RATIO_ARG_PREFIX}{_FIO_SIZE_RATIOS[pattern]}"


def _cpu_scaled_stressors(*arg_names: str) -> dict[LoadPattern, dict[str, Any]]:
    """Create CPU-scaled stressor arguments for multiple argument names.

    Args:
        *arg_names: The names of arguments to scale by CPU.

    Returns:
        A dictionary mapping each LoadPattern to a dictionary of scaled arguments.
    """
    return {
        pattern: {arg_name: _cpu_scaled_arg(pattern) for arg_name in arg_names}
        for pattern in LoadPattern
    }


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
    TestKind.DIAGNOSTIC: (StageTemplate("systemd_boot", LoadPattern.SOFT, 1.00),),
}

_STRESS_ARGS: dict[Subsystem, dict[LoadPattern, dict[str, Any]]] = {
    Subsystem.SYSTEM: {
        LoadPattern.SOFT: {"cpu": 1, "cpu_method": "matrixprod"},
        LoadPattern.BALANCED: {"cpu": 0, "cpu_method": "all"},
        LoadPattern.INTENSE: {"cpu": 0, "cpu_method": "all"},
        LoadPattern.EXTREME: {"cpu": 0, "cpu_method": "all"},
        LoadPattern.SPIKE: {"cpu": 0, "cpu_method": "all"},
    },
    Subsystem.IPC: _cpu_scaled_stressors("mq", "pipe", "sem", "shm"),
    Subsystem.MEMORY: {
        pattern: {
            "vm": _cpu_scaled_arg(pattern),
            "vm_method": "all",
            "vm_bytes": _VM_BYTES[pattern],
            **({"vm-populate": True} if pattern in _VM_POPULATE_PATTERNS else {}),
        }
        for pattern in LoadPattern
    },
    Subsystem.NETWORK: {
        pattern: {"sock": _cpu_scaled_arg(pattern), "sock_ops": _SOCK_OPS[pattern]}
        for pattern in LoadPattern
    },
    Subsystem.SYSCALLS: _cpu_scaled_stressors("syscall"),
}

_FIO_ARGS: dict[LoadPattern, dict[str, Any]] = {
    LoadPattern.SOFT: {
        "readwrite": "read",
        "bs": "128k",
        "numjobs": 1,
        "iodepth": 1,
        "size": _avail_ratio_arg(LoadPattern.SOFT),
    },
    LoadPattern.BALANCED: {
        "readwrite": "randrw",
        "bs": "16k",
        "numjobs": 2,
        "iodepth": 4,
        "size": _avail_ratio_arg(LoadPattern.BALANCED),
    },
    LoadPattern.INTENSE: {
        "readwrite": "randrw",
        "bs": "4k",
        "numjobs": 4,
        "iodepth": 16,
        "size": _avail_ratio_arg(LoadPattern.INTENSE),
    },
    LoadPattern.EXTREME: {
        "readwrite": "randwrite",
        "bs": "4k",
        "numjobs": 6,
        "iodepth": 24,
        "size": _avail_ratio_arg(LoadPattern.EXTREME),
    },
    LoadPattern.SPIKE: {
        "readwrite": "randwrite",
        "bs": "4k",
        "numjobs": 6,
        "iodepth": 24,
        "size": _avail_ratio_arg(LoadPattern.SPIKE),
    },
}


def build_task(
    subsystem: Subsystem,
    pattern: LoadPattern,
    stage_duration_sec: int,
) -> LoadTask:
    """Build a LoadTask for a given subsystem, pattern, and duration.

    Args:
        subsystem: The subsystem to test (file, IPC, memory, network, syscalls, system).
        pattern: The load pattern to use (soft, balanced, intense, extreme, spike).
        stage_duration_sec: The duration of the task in seconds.

    Returns:
        A LoadTask configured for the specified subsystem and pattern.
    """
    if subsystem is Subsystem.FILE:
        args = _FIO_ARGS[pattern]
        args["runtime_sec"] = stage_duration_sec
        return LoadTask(subsystem=subsystem, tool="fio", args=args)

    subsystem_args = _STRESS_ARGS[subsystem]
    args = subsystem_args[pattern]
    args["timeout_sec"] = stage_duration_sec
    return LoadTask(subsystem=subsystem, tool="stress-ng", args=args)


def build_stage_tasks(
    test_kind: TestKind,
    subsystems: frozenset[Subsystem],
    pattern: LoadPattern,
    stage_duration_sec: int,
) -> tuple[LoadTask, ...]:
    """Build a tuple of LoadTasks for a stage based on test kind.

    For diagnostic tests, returns predefined systemd-analyze tasks.
    For other test kinds, builds tasks for each subsystem with the given pattern.

    Args:
        test_kind: The kind of test being performed.
        subsystems: The set of subsystems to test.
        pattern: The load pattern to use for non-diagnostic tests.
        stage_duration_sec: The duration of each task in seconds.

    Returns:
        A tuple of LoadTasks configured for the stage.
    """
    if test_kind is TestKind.DIAGNOSTIC:
        return (
            LoadTask(subsystem=Subsystem.SYSTEM, tool="systemd-analyze", args={"opt": "time"}),
            LoadTask(
                subsystem=Subsystem.SYSTEM,
                tool="systemd-analyze",
                args={"opt": "critical-chain"},
            ),
        )
    return tuple(
        build_task(ss, pattern, stage_duration_sec)
        for ss in sorted(subsystems, key=lambda item: item.value)
    )
