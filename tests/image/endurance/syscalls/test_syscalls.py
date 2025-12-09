import logging
from pathlib import Path

import pytest
from image.utils import env_var_to_type_or_exit

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders.stress_ng import StressNg
from imgtests.logger import set_handlers

logger = logging.getLogger(__name__)
set_handlers(logger, Path("syscalls.log"))

SSH_PASSWORD = env_var_to_type_or_exit("SSH_PASS", str, logger)
SSH_USER = env_var_to_type_or_exit("SSH_USER", str, logger)
SSH_ADDR = env_var_to_type_or_exit("SSH_ADDR", str, logger)
SSH_PORT = env_var_to_type_or_exit("SSH_PORT", int, logger)


@pytest.fixture(scope="session")
def ssh_client() -> SSHClient:
    return SSHClient(SSH_ADDR, SSH_USER, SSH_PASSWORD, SSH_PORT)


@pytest.fixture(scope="session")
def stress_ng(ssh_client: SSHClient) -> StressNg:
    return StressNg(ssh_client)


def _assert_metrics_sane_for_stressor(stressor_name: str, metrics) -> None:
    selected = [m for m in metrics if m.stressor == stressor_name]
    assert selected, f"No metrics found for stressor '{stressor_name}': {metrics!r}"

    for m in selected:
        assert m.stressor == stressor_name

        assert isinstance(m.bogo_ops, int)
        assert m.bogo_ops >= 0

        assert isinstance(m.real_time_secs, float)
        assert m.real_time_secs > 0.0

        assert isinstance(m.usr_time_secs, float)
        assert m.usr_time_secs >= 0.0

        assert isinstance(m.sys_time_secs, float)
        assert m.sys_time_secs >= 0.0

        assert isinstance(m.bogo_ops_s_real_time, float)
        assert m.bogo_ops_s_real_time >= 0.0

        assert isinstance(m.bogo_ops_s_usr_sys_time, float)
        assert m.bogo_ops_s_usr_sys_time >= 0.0

        assert isinstance(m.cpu_used_per_instance, float)
        assert 0.0 <= m.cpu_used_per_instance <= 100.0

        if m.rss_max_kb is not None:
            assert isinstance(m.rss_max_kb, int)
            assert m.rss_max_kb >= 0


def _assert_summary_sane(summary) -> None:
    assert summary is not None, "Run summary was not parsed from stress-ng output"

    assert isinstance(summary.skipped, int)
    assert isinstance(summary.passed, int)
    assert isinstance(summary.failed, int)
    assert isinstance(summary.metrics_untrustworthy, int)

    assert summary.skipped >= 0
    assert summary.passed >= 0
    assert summary.failed >= 0
    assert summary.metrics_untrustworthy >= 0

    assert summary.skipped + summary.passed + summary.failed >= 1

    assert summary.failed == 0
    assert summary.metrics_untrustworthy == 0


def _assert_syscall_top10_slowest(metrics, limit: int = 10) -> None:
    syscall_metrics = [m for m in metrics if m.stressor == "syscall"]
    assert syscall_metrics, "No syscall metrics found"

    m = syscall_metrics[0]
    top10 = m.top10_slowest
    assert top10, "top10_slowest for syscall is empty or None"

    assert 1 <= len(top10) <= limit

    for entry in top10:
        assert isinstance(entry, tuple)
        assert len(entry) == 4
        name, avg_ns, min_ns, max_ns = entry

        assert isinstance(name, str)
        assert name

        assert isinstance(avg_ns, float)
        assert isinstance(min_ns, int)
        assert isinstance(max_ns, int)

        assert min_ns <= avg_ns <= max_ns, (
            f"Invalid timing bounds for syscall {name}: min={min_ns}, avg={avg_ns}, max={max_ns}"
        )

    avgs = [e[1] for e in top10]
    assert avgs == sorted(avgs, reverse=True), f"top10_slowest is not sorted by avg_ns desc: {avgs}"


def test_syscalls_all_endurance(stress_ng: StressNg) -> None:
    result, (metrics, summary) = stress_ng.run(
        timeout_sec=20,
        syscall=1,
        syscall_method="all",
    )

    assert result.returncode == 0, (
        f"stress-ng exited with {result.returncode}\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    assert metrics, "No metrics parsed from stress-ng output"

    _assert_metrics_sane_for_stressor("syscall", metrics)
    _assert_summary_sane(summary)
    _assert_syscall_top10_slowest(metrics, limit=10)


def test_syscalls_with_other_stressors_parsed_together(stress_ng: StressNg) -> None:
    result, (metrics, summary) = stress_ng.run(
        timeout_sec=20,
        cpu=1,
        cpu_method="all",
        syscall=1,
        syscall_method="all",
    )

    assert result.returncode == 0, (
        f"stress-ng exited with {result.returncode}\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    assert metrics, "No metrics parsed from stress-ng output"

    _assert_metrics_sane_for_stressor("syscall", metrics)
    _assert_metrics_sane_for_stressor("cpu", metrics)
    _assert_summary_sane(summary)
    _assert_syscall_top10_slowest(metrics, limit=10)
