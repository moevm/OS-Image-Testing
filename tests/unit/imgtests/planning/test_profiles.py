"""Unit tests for the profiles module."""

import pytest

from imgtests.planning.models import LoadPattern, LoadTask
from imgtests.planning.models import TestKind as ProfilesTestKind
from imgtests.planning.profiles import (
    _avail_ratio_arg,
    _cpu_scaled_arg,
    _cpu_scaled_stressors,
    build_stage_tasks,
    build_task,
)
from imgtests.types import Subsystem


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        (LoadPattern.SOFT, "@cpu:0.25"),
        (LoadPattern.BALANCED, "@cpu:0.5"),
        (LoadPattern.INTENSE, "@cpu:1.0"),
        (LoadPattern.EXTREME, "@cpu:1.5"),
        (LoadPattern.SPIKE, "@cpu:2.0"),
    ],
)
def test__cpu_scaled_arg(pattern: LoadPattern, expected: str) -> None:
    assert _cpu_scaled_arg(pattern) == expected


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        (LoadPattern.SOFT, "@avail_ratio:0.025"),
        (LoadPattern.BALANCED, "@avail_ratio:0.05"),
        (LoadPattern.INTENSE, "@avail_ratio:0.075"),
        (LoadPattern.EXTREME, "@avail_ratio:0.1"),
        (LoadPattern.SPIKE, "@avail_ratio:0.1"),
    ],
)
def test__avail_ratio_arg(pattern: LoadPattern, expected: str) -> None:
    assert _avail_ratio_arg(pattern) == expected


def test__cpu_scaled_stressors() -> None:
    result = _cpu_scaled_stressors("mq", "pipe", "sem")

    assert result[LoadPattern.SOFT] == {"mq": "@cpu:0.25", "pipe": "@cpu:0.25", "sem": "@cpu:0.25"}
    assert result[LoadPattern.BALANCED] == {"mq": "@cpu:0.5", "pipe": "@cpu:0.5", "sem": "@cpu:0.5"}
    assert result[LoadPattern.INTENSE] == {"mq": "@cpu:1.0", "pipe": "@cpu:1.0", "sem": "@cpu:1.0"}
    assert result[LoadPattern.EXTREME] == {"mq": "@cpu:1.5", "pipe": "@cpu:1.5", "sem": "@cpu:1.5"}
    assert result[LoadPattern.SPIKE] == {"mq": "@cpu:2.0", "pipe": "@cpu:2.0", "sem": "@cpu:2.0"}


class TestBuildTask:
    """Tests for the build_task function."""

    def test_build_task_file_system(self) -> None:
        task = build_task(Subsystem.FILE, LoadPattern.BALANCED, 120)

        assert task.subsystem == Subsystem.FILE
        assert task.tool == "fio"
        assert task.args == {
            "readwrite": "randrw",
            "bs": "16k",
            "numjobs": 2,
            "iodepth": 4,
            "size": "@avail_ratio:0.05",
            "runtime_sec": 120,
        }

    def test_build_task_memory_system(self) -> None:
        task = build_task(Subsystem.MEMORY, LoadPattern.INTENSE, 60)

        assert task.subsystem == Subsystem.MEMORY
        assert task.tool == "stress-ng"
        assert task.args == {
            "vm": "@cpu:1.0",
            "vm_method": "all",
            "vm_bytes": "35%",
            "timeout_sec": 60,
        }

    @pytest.mark.parametrize(
        ("subsystem", "pattern", "expected"),
        [
            (Subsystem.MEMORY, LoadPattern.SOFT, False),
            (Subsystem.MEMORY, LoadPattern.BALANCED, False),
            (Subsystem.MEMORY, LoadPattern.INTENSE, False),
            (Subsystem.MEMORY, LoadPattern.EXTREME, True),
            (Subsystem.MEMORY, LoadPattern.SPIKE, True),
        ],
    )
    def test_build_task_memory_system_populate(
        self,
        subsystem: Subsystem,
        pattern: LoadPattern,
        expected: bool,
    ) -> None:
        assert build_task(subsystem, pattern, 60).args.get("vm-populate", False) is expected

    def test_build_task_ipc_system(self) -> None:
        task = build_task(Subsystem.IPC, LoadPattern.BALANCED, 90)

        assert task.subsystem == Subsystem.IPC
        assert task.tool == "stress-ng"
        assert task.args == {
            "mq": "@cpu:0.5",
            "pipe": "@cpu:0.5",
            "sem": "@cpu:0.5",
            "shm": "@cpu:0.5",
            "timeout_sec": 90,
        }

    def test_build_task_network_system(self) -> None:
        task = build_task(Subsystem.NETWORK, LoadPattern.INTENSE, 60)

        assert task.subsystem == Subsystem.NETWORK
        assert task.tool == "stress-ng"
        assert task.args == {
            "sock": "@cpu:1.0",
            "sock_ops": 250_000,
            "timeout_sec": 60,
        }

    def test_build_task_syscalls_system(self) -> None:
        task = build_task(Subsystem.SYSCALLS, LoadPattern.SOFT, 45)

        assert task.subsystem == Subsystem.SYSCALLS
        assert task.tool == "stress-ng"
        assert task.args == {
            "syscall": "@cpu:0.25",
            "timeout_sec": 45,
        }

    def test_build_task_system_system(self) -> None:
        task = build_task(Subsystem.SYSTEM, LoadPattern.SOFT, 30)

        assert task.subsystem == Subsystem.SYSTEM
        assert task.tool == "stress-ng"
        assert task.args == {
            "cpu": 1,
            "cpu_method": "matrixprod",
            "timeout_sec": 30,
        }


class TestBuildStageTasks:
    """Tests for the build_stage_tasks function."""

    def test_build_stage_tasks_diagnostic(self) -> None:
        subsystems = frozenset({Subsystem.MEMORY, Subsystem.NETWORK})
        tasks = build_stage_tasks(ProfilesTestKind.DIAGNOSTIC, subsystems, LoadPattern.SOFT, 60)

        assert tasks == (
            LoadTask(subsystem=Subsystem.SYSTEM, tool="systemd-analyze", args={"opt": "time"}),
            LoadTask(
                subsystem=Subsystem.SYSTEM,
                tool="systemd-analyze",
                args={"opt": "critical-chain"},
            ),
        )

    def test_build_stage_tasks_for_subsystems(self) -> None:
        subsystems = frozenset({Subsystem.MEMORY, Subsystem.NETWORK, Subsystem.SYSTEM})
        tasks = build_stage_tasks(ProfilesTestKind.LOAD, subsystems, LoadPattern.BALANCED, 120)

        assert len(tasks) == 3  # noqa: PLR2004
        # Tasks should be sorted by subsystem name
        assert tasks[0].subsystem == Subsystem.MEMORY
        assert tasks[1].subsystem == Subsystem.NETWORK
        assert tasks[2].subsystem == Subsystem.SYSTEM

        for task in tasks:
            assert task.args["timeout_sec"] == 120  # noqa: PLR2004

    def test_build_stage_tasks_single_subsystem(self) -> None:
        """Test building stage tasks for a single subsystem."""
        subsystems = frozenset({Subsystem.SYSTEM})
        tasks = build_stage_tasks(ProfilesTestKind.STRESS, subsystems, LoadPattern.EXTREME, 90)

        assert len(tasks) == 1
        assert tasks[0].subsystem == Subsystem.SYSTEM
        assert tasks[0].tool == "stress-ng"
        assert tasks[0].args == {
            "cpu": 0,
            "cpu_method": "all",
            "timeout_sec": 90,
        }

    def test_build_stage_tasks_sorted_subsystems(self) -> None:
        subsystems = frozenset({Subsystem.SYSCALLS, Subsystem.MEMORY, Subsystem.SYSTEM})
        tasks = build_stage_tasks(ProfilesTestKind.STABILITY, subsystems, LoadPattern.BALANCED, 60)

        assert len(tasks) == 3  # noqa: PLR2004
        assert tasks[0].subsystem == Subsystem.MEMORY
        assert tasks[1].subsystem == Subsystem.SYSCALLS
        assert tasks[2].subsystem == Subsystem.SYSTEM
