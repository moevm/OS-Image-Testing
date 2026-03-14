import logging
from pathlib import Path
from typing import TYPE_CHECKING

from imgtests.exec.loaders.dmsetup import DeviceMapperSetup, setup_block_device
from imgtests.runner import AbstractRunnableTimeLimitedTest, Subsystem
from imgtests.suites.drive.fio import FioSuite, FioSuiteConfig, FioWorkload

if TYPE_CHECKING:
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
    ) -> None:
        cfg = FioSuiteConfig(
            suite="scaling",
            duration_sec=timeout,
            results_dir=Path().home() / "fio",
            workloads=SCALING_WORKLOADS,
        )
        out = FioSuite(client, cfg).run()
        self.logger.info("FIO scaling PASSED: %s", out)


class FioDisksNightly(AbstractRunnableTimeLimitedTest):
    """Tests that run fio on a disk with nightly workloads."""

    def __init__(self, timeout: int) -> None:
        super().__init__("Nightly load drives with fio.", frozenset({Subsystem.FILE}), timeout)

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> None:
        cfg = FioSuiteConfig(
            suite="nightly",
            duration_sec=timeout,
            results_dir=Path().home() / "fio",
            workloads=NIGHTLY_WORKLOADS,
        )
        out = FioSuite(client, cfg).run()
        logger.info("FIO nightly PASSED: %s", out)


class FioDisksDMDelay(AbstractRunnableTimeLimitedTest):
    """Tests that run fio on a disk with dm-delay."""

    def __init__(self, timeout: int) -> None:
        super().__init__("Dm-delay test with fio.", frozenset({Subsystem.FILE}), timeout)

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> None:
        if not setup_block_device(ssh_client=client):
            logger.error("Error in block device setup.")
            return

        dm = DeviceMapperSetup(client)
        if not dm.create_dm_delay_device():
            logger.error("Error in creating dm-delay device.")
            return

        cfg = FioSuiteConfig(
            suite="dm-delay",
            duration_sec=timeout,
            results_dir=Path().home() / "fio",
            workloads=SCALING_WORKLOADS,
            filename="/dev/mapper/delay1",
        )
        out = FioSuite(client, cfg).run()
        logger.info("FIO dm-delay PASSED: %s", out)


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
    ) -> None:
        if not setup_block_device(ssh_client=client):
            logger.error("Error in block device setup.")
            return

        dm = DeviceMapperSetup(client)
        if not dm.create_dm_dust_device():
            logger.error("Error in creating dm-delay device.")
            return
        dm.add_bad_blocks(device_name="dust1", block_numbers=list(range(50, 100)))

        read_cfg = FioSuiteConfig(
            suite="dm-dust",
            duration_sec=timeout,
            results_dir=Path().home() / "fio",
            workloads=DMDUST_READ_WORKLOAD,
            filename="/dev/mapper/dust1",
        )
        write_cfg = FioSuiteConfig(
            suite="dm-dust",
            duration_sec=timeout,
            results_dir=Path().home() / "fio",
            workloads=DMDUST_WRITE_WORKLOAD,
            filename="/dev/mapper/dust1",
        )

        try:
            FioSuite(client, read_cfg).run()
        except RuntimeError:
            logger.info("Error above is intended, dm-dust works.")

        out = FioSuite(client, write_cfg).run()
        logger.info("FIO dm-dust PASSED: %s", out)
