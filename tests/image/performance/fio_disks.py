import logging
import queue
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from imgtests.database.database import ImgtestsDatabase, UtilityResultRecord
from imgtests.exec.loaders.dmsetup import DeviceMapperSetup, setup_block_device
from imgtests.exec.observers.resource import get_available_ram_size
from imgtests.exec.osinfo import get_os_release
from imgtests.runner import AbstractRunnableTimeLimitedTest, TestResult, TestStatus
from imgtests.suites.drive.fio import FioSuite, FioSuiteConfig, FioWorkload
from imgtests.sysrep import get_system_info
from imgtests.types import Distro, Subsystem

if TYPE_CHECKING:
    from collections.abc import Iterable
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


logger = logging.getLogger(__name__)

FIO_RESULTS_DIR = Path.home() / "fio"


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


class _FioDisksBaseTest(AbstractRunnableTimeLimitedTest):
    def __init__(
        self,
        description: str,
        timeout: int,
        *,
        db: ImgtestsDatabase | None = None,
        config_id: int | None = None,
        experiment_description: str | None = None,
    ) -> None:
        super().__init__(description, frozenset({Subsystem.FILE}), timeout)
        self.db = db or ImgtestsDatabase()
        self.config_id = config_id
        self.experiment_description = experiment_description

    def run_fio_suite(
        self,
        client: SSHClient | None,
        timeout: int,
        cfg: FioSuiteConfig,
        *,
        success_msg: str,
        default_experiment_description: str,
    ) -> Iterable[TestResult]:
        started_at = datetime.now(UTC)
        suite_results: list[TestResult] = []

        for result in FioSuite(client, cfg).run():
            suite_results.append(result)
            yield result

        ended_at = datetime.now(UTC)
        self._write_suite_result_to_db(
            client=client,
            timeout=timeout,
            cfg=cfg,
            suite_results=tuple(suite_results),
            started_at=started_at,
            ended_at=ended_at,
            default_experiment_description=default_experiment_description,
        )
        self.logger.info("%s cases=%d", success_msg, len(suite_results))

    def _write_suite_result_to_db(  # noqa: PLR0913
        self,
        *,
        client: SSHClient | None,
        timeout: int,
        cfg: FioSuiteConfig,
        suite_results: tuple[TestResult, ...],
        started_at: datetime,
        ended_at: datetime,
        default_experiment_description: str,
    ) -> None:
        if self.config_id is None:
            cfg_record = self.db.insert_from_system_info(get_system_info(client))
            self.config_id = int(cfg_record.config_id)

        experiment = self.db.insert_experiment(
            config_id=int(self.config_id),
            description=self.experiment_description or default_experiment_description,
            experiment_type="performance",
            started_at=started_at,
            ended_at=ended_at,
        )
        self.db.insert_utility_result(
            UtilityResultRecord(
                experiment_id=int(experiment.experiment_id),
                utility="fio",
                command=("fio-suite", cfg.suite),
                result={
                    "suite": cfg.suite,
                    "timeout_sec": timeout,
                    "results_dir": cfg.results_dir,
                    "workloads": cfg.workloads,
                    "filename": cfg.filename,
                    "results_count": len(suite_results),
                    "results": suite_results,
                },
                description=f"fio suite result: {cfg.suite}",
                started_at=started_at,
                ended_at=ended_at,
                context={"test_name": type(self).__name__},
            ),
        )


class FioDisksScalingTest(_FioDisksBaseTest):
    """Test that runs fio on a disk with scaling workloads."""

    def __init__(
        self,
        timeout: int,
        db: ImgtestsDatabase | None = None,
        config_id: int | None = None,
        experiment_description: str | None = None,
    ) -> None:
        super().__init__(
            "Scaling load drives with fio.",
            timeout,
            db=db,
            config_id=config_id,
            experiment_description=experiment_description,
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
            results_dir=FIO_RESULTS_DIR,
            workloads=SCALING_WORKLOADS,
        )
        yield from self.run_fio_suite(
            client=client,
            timeout=timeout,
            cfg=cfg,
            success_msg="FIO scaling PASSED.",
            default_experiment_description="fio suite 'scaling' run",
        )


class FioDisksNightly(_FioDisksBaseTest):
    """Tests that run fio on a disk with nightly workloads."""

    def __init__(
        self,
        timeout: int,
        db: ImgtestsDatabase | None = None,
        config_id: int | None = None,
        experiment_description: str | None = None,
    ) -> None:
        super().__init__(
            "Nightly load drives with fio.",
            timeout,
            db=db,
            config_id=config_id,
            experiment_description=experiment_description,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        cfg = FioSuiteConfig(
            suite="nightly",
            duration_sec=timeout,
            results_dir=FIO_RESULTS_DIR,
            workloads=NIGHTLY_WORKLOADS,
        )
        yield from self.run_fio_suite(
            client=client,
            timeout=timeout,
            cfg=cfg,
            success_msg="FIO nightly PASSED.",
            default_experiment_description="fio suite 'nightly' run",
        )


class FioDisksDMDelay(_FioDisksBaseTest):
    """Tests that run fio on a disk with dm-delay."""

    def __init__(
        self,
        timeout: int,
        db: ImgtestsDatabase | None = None,
        config_id: int | None = None,
        experiment_description: str | None = None,
    ) -> None:
        super().__init__(
            "Dm-delay test with fio.",
            timeout,
            db=db,
            config_id=config_id,
            experiment_description=experiment_description,
        )

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> Iterable[TestResult]:
        os_id = get_os_release(client).id
        if os_id and os_id != Distro.POKY.value:
            self.logger.warning("Skipping test due dm-delay test is only supported on poky.")
            yield TestResult(status=TestStatus.SKIPPED)
            return

        result = setup_block_device(client=client)
        if result is not None and result.returncode:
            logger.error("Error in block device setup.")
            yield TestResult(status=TestStatus.BROKEN)
            return

        dm = DeviceMapperSetup(client)
        result = dm.create_dm_delay_device()
        if result.returncode:
            logger.error("Error in creating dm-delay device.")
            yield TestResult(status=TestStatus.BROKEN)
            return

        cfg = FioSuiteConfig(
            suite="dm-delay",
            duration_sec=timeout,
            results_dir=FIO_RESULTS_DIR,
            workloads=SCALING_WORKLOADS,
            filename=Path("/dev/mapper/delay1"),
        )

        try:
            yield from self.run_fio_suite(
                client=client,
                timeout=timeout,
                cfg=cfg,
                success_msg="FIO dm-delay PASSED.",
                default_experiment_description="fio suite 'dm-delay' run",
            )
        finally:
            dm.remove_dm_device(device_name="delay1")


class FioDisksDMDust(_FioDisksBaseTest):
    """Tests that run fio on a disk with dm-dust."""

    def __init__(
        self,
        timeout: int,
        db: ImgtestsDatabase | None = None,
        config_id: int | None = None,
        experiment_description: str | None = None,
    ) -> None:
        super().__init__(
            "Dm-dust fio test with errors on read.",
            timeout,
            db=db,
            config_id=config_id,
            experiment_description=experiment_description,
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
            yield TestResult(status=TestStatus.SKIPPED)
            return

        result = setup_block_device(client=client)
        if result is not None and result.returncode:
            logger.error("Error in block device setup.")
            yield TestResult(status=TestStatus.BROKEN)
            return

        dm = DeviceMapperSetup(client)
        result = dm.create_dm_dust_device()
        if result.returncode:
            logger.error("Error in creating dm-dust device.")
            yield TestResult(status=TestStatus.BROKEN)
            return

        try:
            result = dm.add_bad_blocks(device_name="dust1", block_numbers=list(range(50, 100)))
            if result.returncode:
                logger.error("Error in adding bad blocks to dm-dust device.")
                yield TestResult(status=TestStatus.BROKEN)
                return

            read_cfg = FioSuiteConfig(
                suite="dm-dust",
                duration_sec=timeout,
                results_dir=FIO_RESULTS_DIR,
                workloads=DMDUST_READ_WORKLOAD,
                filename=Path("/dev/mapper/dust1"),
            )
            write_cfg = FioSuiteConfig(
                suite="dm-dust",
                duration_sec=timeout,
                results_dir=FIO_RESULTS_DIR,
                workloads=DMDUST_WRITE_WORKLOAD,
                filename=Path("/dev/mapper/dust1"),
            )

            read_results = tuple(FioSuite(client, read_cfg).run())
            if any(result.status is TestStatus.FAILED for result in read_results):
                logger.info("dm-dust read workload failed as expected.")
            else:
                logger.warning("dm-dust read workload completed without the expected error.")

            yield from self.run_fio_suite(
                client=client,
                timeout=timeout,
                cfg=write_cfg,
                success_msg="FIO dm-dust PASSED.",
                default_experiment_description="fio suite 'dm-dust' run",
            )
        finally:
            dm.remove_dm_device(device_name="dust1")


class FioDisksVariationTest(_FioDisksBaseTest):
    """Test that runs fio on a disk with variations of bs, rw and offset."""

    def __init__(
        self,
        timeout: int,
        db: ImgtestsDatabase | None = None,
        config_id: int | None = None,
        experiment_description: str | None = None,
    ) -> None:
        super().__init__(
            "Fio parameter variation test.",
            timeout,
            db=db,
            config_id=config_id,
            experiment_description=experiment_description,
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
        size = _calculate_fio_ram_percent(50, client)

        for offset, offset_incr in offset_cases:
            cfg = FioSuiteConfig(
                suite=f"variation-offset-{offset}-{offset_incr or 'none'}",
                duration_sec=timeout,
                results_dir=FIO_RESULTS_DIR,
                workloads=workloads,
                offset=offset,
                offset_increment=offset_incr,
                size=size,
                filename=Path(f"variation_offset_{offset}_{offset_incr or 'none'}_testfile"),
            )
            yield from self.run_fio_suite(
                client=client,
                timeout=timeout,
                cfg=cfg,
                success_msg=f"FIO variation offset={offset}, incr={offset_incr} PASSED.",
                default_experiment_description=(
                    f"fio suite 'variation' offset={offset} incr={offset_incr or 'none'} run"
                ),
            )


class FioDisksParallelLoadTest(_FioDisksBaseTest):
    """Test that runs fio parallel mixed workloads."""

    def __init__(
        self,
        timeout: int,
        db: ImgtestsDatabase | None = None,
        config_id: int | None = None,
        experiment_description: str | None = None,
    ) -> None:
        super().__init__(
            "Fio parallel load test.",
            timeout,
            db=db,
            config_id=config_id,
            experiment_description=experiment_description,
        )

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
                results_dir=FIO_RESULTS_DIR,
                workloads=SMALL_BLOCK_WORKLOAD,
                size=size,
                filename=Path("small_testfile"),
            ),
            FioSuiteConfig(
                suite="large",
                duration_sec=timeout,
                results_dir=FIO_RESULTS_DIR,
                workloads=LARGE_BLOCK_WORKLOAD,
                size=size,
                filename=Path("large_testfile"),
            ),
            FioSuiteConfig(
                suite="large-with-offset",
                duration_sec=timeout,
                results_dir=FIO_RESULTS_DIR,
                workloads=LARGE_BLOCK_WORKLOAD,
                offset_increment="3k",
                size=size,
                filename=Path("large_with_offset_testfile"),
            ),
        ]
        q: queue.Queue[TestResult] = queue.Queue()
        futures = [
            executor.submit(
                _enqueue_fio_results,
                self,
                client,
                timeout,
                cfg,
                "FIO parallel load test PASSED.",
                q,
            )
            for cfg in configs
        ]
        while any(not future.done() for future in futures) or not q.empty():
            try:
                yield q.get(timeout=0.5)
            except queue.Empty:
                continue
        for future in futures:
            future.result()


def _enqueue_fio_results(  # noqa: PLR0913
    runner: _FioDisksBaseTest,
    client: SSHClient | None,
    timeout: int,
    cfg: FioSuiteConfig,
    msg: str,
    q: queue.Queue[TestResult],
) -> None:
    for result in runner.run_fio_suite(
        client=client,
        timeout=timeout,
        cfg=cfg,
        success_msg=msg,
        default_experiment_description=f"fio suite '{cfg.suite}' run",
    ):
        q.put(result)


def _calculate_fio_ram_percent(percent: int, client: SSHClient | None = None) -> str:
    if percent <= 0 or percent > 100:  # noqa: PLR2004
        return "100MB"
    ram_size = get_available_ram_size(client)
    if ram_size is not None:
        return f"{round(ram_size // 1024 * percent // 100)}MB"
    return "100MB"
