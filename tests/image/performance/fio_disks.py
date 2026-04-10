import logging
import queue
from pathlib import Path
from typing import TYPE_CHECKING

from imgtests.exec.exec import common_run_command
from imgtests.exec.loaders.dmsetup import DeviceMapperSetup, setup_block_device
from imgtests.exec.osinfo import get_os_release
from imgtests.runner import AbstractRunnableTimeLimitedTest, TestResult, TestStatus
from imgtests.suites.drive.fio import FioSuite, FioSuiteConfig, FioWorkload
from imgtests.types import Distro, Subsystem

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


logger = logging.getLogger(__name__)


SCALING_WORKLOADS: tuple[FioWorkload, ...] = (
    FioWorkload("seq_write_1M", "write", "1M", 1.0),
    FioWorkload("seq_write_256k", "write", "256k", 1.0),
    FioWorkload("seq_write_64k", "write", "64k", 1.0),
    FioWorkload("rand_write_64k", "randwrite", "64k", 1.0),
    FioWorkload("rand_write_16k", "randwrite", "16k", 1.0),
    FioWorkload("rand_write_4k", "randwrite", "4k", 1.0),
)

NIGHTLY_WORKLOADS: tuple[FioWorkload, ...] = (
    FioWorkload("seq_write_1M", "write", "1M", 1.0),
    FioWorkload("seq_write_256k", "write", "256k", 1.0),
    FioWorkload("seq_write_64k", "write", "64k", 1.0),
    FioWorkload("seq_read_1M", "read", "1M", 1.0),
    FioWorkload("seq_read_64k", "read", "64k", 1.0),
    FioWorkload("rand_write_64k", "randwrite", "64k", 1.0),
    FioWorkload("rand_write_16k", "randwrite", "16k", 1.0),
    FioWorkload("rand_write_4k", "randwrite", "4k", 1.0),
    FioWorkload("rand_read_16k", "randread", "16k", 1.0),
    FioWorkload("rand_read_4k", "randread", "4k", 1.0),
)

DMDUST_READ_WORKLOAD: tuple[FioWorkload, ...] = (
    FioWorkload("rand_read_1M", "randread", "1M", 1.0),
)

DMDUST_WRITE_WORKLOAD: tuple[FioWorkload, ...] = (FioWorkload("seq_write_1M", "write", "1M", 1.0),)

SMALL_BLOCK_WORKLOAD: tuple[FioWorkload, ...] = (
    FioWorkload("rand_write_512b", "randwrite", "512b", 1.0),
    FioWorkload("rand_write_4k", "randwrite", "4k", 1.0),
    FioWorkload("rand_read_512b", "randread", "512b", 1.0),
    FioWorkload("rand_read_4k", "randread", "4k", 1.0),
)

LARGE_BLOCK_WORKLOAD: tuple[FioWorkload, ...] = (
    FioWorkload("seq_write_1M", "write", "1M", 1.0),
    FioWorkload("seq_write_256k", "write", "256k", 1.0),
    FioWorkload("seq_read_1M", "read", "1M", 1.0),
    FioWorkload("seq_read_256k", "read", "256k", 1.0),
)


class FioDisksScalingTest(AbstractRunnableTimeLimitedTest):
    """Test that runs fio on a disk with scaling workloads."""

    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Scaling load drives with fio.", frozenset({Subsystem.FILE}), timeout=timeout
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        cfg = FioSuiteConfig(
            suite="scaling",
            duration_sec=timeout,
            results_dir=Path().home() / "fio",
            workloads=SCALING_WORKLOADS,
        )
        yield from _handle_fio_suite(client, cfg, "FIO scaling PASSED.")


class FioDisksNightly(AbstractRunnableTimeLimitedTest):
    """Tests that run fio on a disk with nightly workloads."""

    def __init__(self, timeout: int) -> None:
        super().__init__("Nightly load drives with fio.", frozenset({Subsystem.FILE}), timeout)

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        cfg = FioSuiteConfig(
            suite="nightly",
            duration_sec=timeout,
            results_dir=Path().home() / "fio",
            workloads=NIGHTLY_WORKLOADS,
        )
        yield from _handle_fio_suite(client, cfg, "FIO nightly PASSED.")


class FioDisksDMDelay(AbstractRunnableTimeLimitedTest):
    """Tests that run fio on a disk with dm-delay."""

    def __init__(self, timeout: int) -> None:
        super().__init__("Dm-delay test with fio.", frozenset({Subsystem.FILE}), timeout)

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        os_id = get_os_release(client).id
        if os_id and os_id != Distro.POKY.value:
            self.logger.warning("Skipping test due dm-delay test is only supported on poky.")
            return TestResult(status=TestStatus.SKIPPED)

        result = setup_block_device(client=client)
        if result is not None and result.returncode:
            logger.error("Error in block device setup.")
            return TestResult(status=TestStatus.BROKEN)

        dm = DeviceMapperSetup(client)
        result = dm.create_dm_delay_device()
        if result.returncode:
            logger.error("Error in creating dm-delay device.")
            return TestResult(status=TestStatus.BROKEN)

        cfg = FioSuiteConfig(
            suite="dm-delay",
            duration_sec=timeout,
            results_dir=Path().home() / "fio",
            workloads=SCALING_WORKLOADS,
            filename=Path("/dev/mapper/delay1"),
        )

        yield from _handle_fio_suite(client, cfg, "FIO dm-delay PASSED.")
        dm.remove_dm_device(device_name="delay1")


class FioDisksDMDust(AbstractRunnableTimeLimitedTest):
    """Tests that run fio on a disk with dm-dust."""

    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Dm-dust fio test with errors on read.", frozenset({Subsystem.FILE}), timeout
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        os_id = get_os_release(client).id
        if os_id and os_id != Distro.POKY.value:
            self.logger.warning("Skipping test due dm-dust test is only supported on poky.")
            return TestResult(status=TestStatus.SKIPPED)

        result = setup_block_device(client=client)
        if result is not None and result.returncode:
            logger.error("Error in block device setup.")
            return TestResult(status=TestStatus.BROKEN)

        dm = DeviceMapperSetup(client)
        result = dm.create_dm_dust_device()
        if result.returncode:
            logger.error("Error in creating dm-delay device.")
            return TestResult(status=TestStatus.BROKEN)
        result = dm.add_bad_blocks(device_name="dust1", block_numbers=list(range(50, 100)))
        if result.returncode:
            return TestResult(status=TestStatus.BROKEN)

        read_cfg = FioSuiteConfig(
            suite="dm-dust",
            duration_sec=timeout,
            results_dir=Path().home() / "fio",
            workloads=DMDUST_READ_WORKLOAD,
            filename=Path("/dev/mapper/dust1"),
        )
        write_cfg = FioSuiteConfig(
            suite="dm-dust",
            duration_sec=timeout,
            results_dir=Path().home() / "fio",
            workloads=DMDUST_WRITE_WORKLOAD,
            filename=Path("/dev/mapper/dust1"),
        )

        try:
            FioSuite(client, read_cfg).run()
        except RuntimeError:
            logger.info("Error above is intended, dm-dust works.")

        yield from _handle_fio_suite(client, write_cfg, "FIO dm-dust PASSED.")
        dm.remove_dm_device(device_name="dust1")


class FioDisksVariationTest(AbstractRunnableTimeLimitedTest):
    """Test that runs fio on a disk with variations of bs, rw and offset."""

    def __init__(self, timeout: int) -> None:
        super().__init__(
            "Fio parameter variation test.", frozenset({Subsystem.FILE}), timeout=timeout
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        bs_values = ["512b", "4k", "2m", "4m"]
        rw_values = ["write", "read", "randread", "randwrite"]
        offset_cases = [
            ("0", "0"),
            ("512b", None),
            ("0", "3k"),
        ]
        workloads = tuple(
            FioWorkload(f"{rw}_{bs}", rw=rw, bs=bs, weight=1.0)
            for bs in bs_values
            for rw in rw_values
        )

        for offset, offset_incr in offset_cases:
            cfg = FioSuiteConfig(
                suite=f"variation-offset-{offset}-{offset_incr or 'none'}",
                duration_sec=timeout,
                results_dir=Path().home() / "fio",
                workloads=workloads,
                offset=offset,
                offset_increment=offset_incr,
                size=_calculate_fio_ram_percent(50, client),
            )
            yield from _handle_fio_suite(
                client, cfg, f"FIO variation offset={offset}, incr={offset_incr} PASSED."
            )


class FioDisksParallelLoadTest(AbstractRunnableTimeLimitedTest):
    """Test that runs fio parallel mixed workloads."""

    def __init__(self, timeout: int) -> None:
        super().__init__("Fio parallel load test.", frozenset({Subsystem.FILE}), timeout=timeout)

    def _run(
        self,
        executor: ThreadPoolExecutor,
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        size = _calculate_fio_ram_percent(10, client)
        configs = [
            FioSuiteConfig(
                suite="small",
                duration_sec=timeout,
                results_dir=Path().home() / "fio",
                workloads=SMALL_BLOCK_WORKLOAD,
                size=size,
            ),
            FioSuiteConfig(
                suite="large",
                duration_sec=timeout,
                results_dir=Path().home() / "fio",
                workloads=LARGE_BLOCK_WORKLOAD,
                size=size,
            ),
            FioSuiteConfig(
                suite="small-with-offset",
                duration_sec=timeout,
                results_dir=Path().home() / "fio",
                workloads=SMALL_BLOCK_WORKLOAD,
                offset="512b",
                offset_increment="3k",
                size=size,
            ),
            FioSuiteConfig(
                suite="large-with-offset",
                duration_sec=timeout,
                results_dir=Path().home() / "fio",
                workloads=LARGE_BLOCK_WORKLOAD,
                offset_increment="3k",
                size=size,
            ),
        ]
        q = queue.Queue()
        for cfg in configs:
            futures = [
                executor.submit(
                    _enqueue_fio_results, client, cfg, "FIO parallel load test PASSED.", q
                )
            ]

        while any(not f.done() for f in futures) or not q.empty():
            try:
                r = q.get(timeout=0.5)
            except queue.Empty:
                continue
            yield r


def _enqueue_fio_results(
    client: SSHClient | None, cfg: FioSuiteConfig, msg: str, q: queue.Queue[TestResult]
) -> None:
    for result in _handle_fio_suite(client, cfg, msg):
        q.put(result)


def _handle_fio_suite(
    client: SSHClient | None, cfg: FioSuiteConfig, msg: str
) -> Iterable[TestResult]:
    fio_gen = FioSuite(client, cfg).run()
    yield from fio_gen
    try:
        next(fio_gen)
    except StopIteration:
        logger.info(msg)


def _calculate_fio_ram_percent(percent: int, client: SSHClient | None = None) -> str:
    if percent <= 0 or percent > 100:  #  noqa: PLR2004
        return "100MB"
    res = common_run_command(
        ["awk '/MemAvailable/ {print $2}' /proc/meminfo"],
        ssh_client=client,
    )
    if res.returncode == 0 and res.stdout.isdigit():
        return f"{round(int(res.stdout) // 1024 * percent // 100)}MB"
    return "100MB"
