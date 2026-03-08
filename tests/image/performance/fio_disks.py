import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from imgtests.database.database import ImgtestsDatabase, UtilityResultRecord
from imgtests.runner import AbstractRunnableTimeLimitedTest
from imgtests.suites.drive.fio import FioSuite, FioSuiteConfig, FioWorkload
from imgtests.sysrep import get_system_info

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


class FioDisksScalingTest(AbstractRunnableTimeLimitedTest):
    """Test that runs fio on a disk with scaling workloads."""

    def __init__(
        self,
        timeout: int,
        db: ImgtestsDatabase | None = None,
        config_id: int | None = None,
        experiment_description: str | None = None,
        write_to_db: bool = True,
    ) -> None:
        super().__init__("Scaling load drives with fio.", {"file"}, timeout=timeout)
        if write_to_db and db is None:
            err_msg = "ImgtestsDatabase must be provided when write_to_db=True."
            raise ValueError(err_msg)
        self.db = db if write_to_db else None
        self.config_id = config_id
        self.experiment_description = experiment_description

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> None:
        results_dir = Path().home() / "fio"
        cfg = FioSuiteConfig(
            suite="scaling",
            duration_sec=timeout,
            results_dir=results_dir,
            workloads=SCALING_WORKLOADS,
        )
        started_at = datetime.now(UTC)
        out = FioSuite(client, cfg).run()
        ended_at = datetime.now(UTC)

        if self.db is not None:
            if self.config_id is None:
                cfg_record = self.db.insert_from_system_info(get_system_info(client))
                self.config_id = int(cfg_record.config_id)

            experiment = self.db.insert_experiment(
                config_id=int(self.config_id),
                description=self.experiment_description or "fio suite 'scaling' run",
                experiment_type="performance",
                started_at=started_at,
                ended_at=ended_at,
            )
            self.db.insert_utility_result(
                UtilityResultRecord(
                    experiment_id=int(experiment.experiment_id),
                    utility="fio",
                    command=("fio-suite", "scaling"),
                    result={
                        "suite": "scaling",
                        "timeout_sec": timeout,
                        "results_dir": results_dir,
                        "workloads": SCALING_WORKLOADS,
                        "result": out,
                    },
                    description="fio suite result: scaling",
                    started_at=started_at,
                    ended_at=ended_at,
                    context={"test_name": type(self).__name__},
                )
            )

        self.logger.info("FIO scaling PASSED: %s", out)


class FioDisksNightly(AbstractRunnableTimeLimitedTest):
    """Tests that run fio on a disk with nightly workloads."""

    def __init__(
        self,
        timeout: int,
        db: ImgtestsDatabase | None = None,
        config_id: int | None = None,
        experiment_description: str | None = None,
        write_to_db: bool = True,
    ) -> None:
        super().__init__("Nightly load drives with fio.", {"file"}, timeout)
        if write_to_db and db is None:
            err_msg = "ImgtestsDatabase must be provided when write_to_db=True."
            raise ValueError(err_msg)
        self.db = db if write_to_db else None
        self.config_id = config_id
        self.experiment_description = experiment_description

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        timeout: int,
    ) -> None:
        results_dir = Path().home() / "fio"
        cfg = FioSuiteConfig(
            suite="nightly",
            duration_sec=timeout,
            results_dir=results_dir,
            workloads=NIGHTLY_WORKLOADS,
        )
        started_at = datetime.now(UTC)
        out = FioSuite(client, cfg).run()
        ended_at = datetime.now(UTC)

        if self.db is not None:
            if self.config_id is None:
                cfg_record = self.db.insert_from_system_info(get_system_info(client))
                self.config_id = int(cfg_record.config_id)

            experiment = self.db.insert_experiment(
                config_id=int(self.config_id),
                description=self.experiment_description or "fio suite 'nightly' run",
                experiment_type="performance",
                started_at=started_at,
                ended_at=ended_at,
            )
            self.db.insert_utility_result(
                UtilityResultRecord(
                    experiment_id=int(experiment.experiment_id),
                    utility="fio",
                    command=("fio-suite", "nightly"),
                    result={
                        "suite": "nightly",
                        "timeout_sec": timeout,
                        "results_dir": results_dir,
                        "workloads": NIGHTLY_WORKLOADS,
                        "result": out,
                    },
                    description="fio suite result: nightly",
                    started_at=started_at,
                    ended_at=ended_at,
                    context={"test_name": type(self).__name__},
                )
            )

        self.logger.info("FIO nightly PASSED: %s", out)
