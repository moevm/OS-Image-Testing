from time import sleep
from typing import TYPE_CHECKING

from imgtests.exec.observers.systemd_analyze import SystemdAnalyze
from imgtests.runner import AbstractRunnableManyTimesTest, Subsystem

if TYPE_CHECKING:
    import logging
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class SystemLoadTimeTest(AbstractRunnableManyTimesTest):
    def __init__(self) -> None:
        super().__init__("System load time.", {Subsystem.SYSTEM})

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        iterations: int,  # noqa: ARG002
    ) -> None:
        result = SystemdAnalyze(client).time()
        sleep_time_sec = 10
        wait_timeout_sec = 600
        while result.total_time < 0 and wait_timeout_sec > 0:
            self.logger.info(
                "Waiting for system to be ready to analyze boot time, %d seconds left.",
                wait_timeout_sec,
            )
            sleep(sleep_time_sec)
            wait_timeout_sec -= sleep_time_sec
            result = SystemdAnalyze(client).time()
        if result.total_time < 0:
            self.logger.error("Failed to get boot time, system might not be ready.")

    def cleanup(self, client: SSHClient | None, logger: logging.Logger) -> None:  # noqa: ARG002
        logger.debug("Noting to cleanup for system load time test.")


class SystemSlowServicesTest(AbstractRunnableManyTimesTest):
    def __init__(self) -> None:
        super().__init__("System slow services.", {Subsystem.SYSTEM})

    def _run(
        self,
        executor: ThreadPoolExecutor,  # noqa: ARG002
        client: SSHClient | None,
        iterations: int,  # noqa: ARG002
    ) -> None:
        self.logger.info(SystemdAnalyze(client).slow_load_services())

    def cleanup(self, client: SSHClient | None, logger: logging.Logger) -> None:  # noqa: ARG002
        logger.debug("Noting to cleanup for system slow services test.")
