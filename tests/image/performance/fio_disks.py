import logging
from pathlib import Path

from imgtests.exec.exec import SSHClient
from imgtests.exec.suites.fio_suite import FioSuiteConfig, FioWorkload, run_fio_suite

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


def test_fio_disks_scaling(remote: SSHClient, duration_sec: int, results_dir: Path) -> None:
    cfg = FioSuiteConfig(
        suite="scaling",
        duration_sec=duration_sec,
        results_dir=results_dir / "fio",
        workloads=SCALING_WORKLOADS,
    )
    out = run_fio_suite(remote, cfg)
    logger.info("FIO scaling PASSED: %s", out)


def test_fio_disks_nightly(remote: SSHClient, duration_sec: int, results_dir: Path) -> None:
    cfg = FioSuiteConfig(
        suite="nightly",
        duration_sec=duration_sec,
        results_dir=results_dir / "fio",
        workloads=NIGHTLY_WORKLOADS,
    )
    out = run_fio_suite(remote, cfg)
    logger.info("FIO nightly PASSED: %s", out)
