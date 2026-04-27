import json
import logging
import re
from typing import TYPE_CHECKING, Any

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient, common_run_command, pipeline
from imgtests.exec.pkgmgrs.mixin import PkgMgrMixin
from imgtests.exec.utils import add_sudo, extract_version, is_timeout_returncode, wrap_with_timeout
from imgtests.results_adapter import AdapterResult, drop_json_fields

if TYPE_CHECKING:
    from imgtests.types import Version


SAVE_RESULT_PATH_PATTERN = re.compile("/[^:]*")
# Default wall-clock limit for a single PTS batch-run before GNU timeout intervenes.
DEFAULT_TEST_TIMEOUT_SEC = 60 * 60
NETWORK_LOOPBACK_TEST_NAME = "pts/network-loopback"

logger = logging.getLogger(__name__)


class PhoronixTestSuite(PkgMgrMixin, GenericUtil):
    def __init__(
        self,
        ssh_client: SSHClient | None = None,
        use_sudo: bool = True,
    ) -> None:
        super().__init__("phoronix-test-suite", ssh_client, use_sudo=use_sudo)

    def install(self) -> ExecResult:
        """Install phoronix-test-suite via the system package manager."""
        if self.path:
            return ExecResult(
                cmd=(),
                stderr=f"{self.name} already has been installed.",
                returncode=0,
            )
        packages = [
            "phoronix-test-suite",
            # TODO: Install all below dependencies only when test requires.
            "gcc",
            "gcc-c++",
            "make",
            "autoconf",
            "Mesa-demo-x",
            "hdparm",
        ]
        return self._install_packages(packages)

    def version(self) -> Version | None:
        result = self(["version"])
        if result.returncode:
            return None
        return extract_version(result.stdout.strip())

    def install_test(self, test_name: str, timeout_sec: int | None = None) -> bool:
        """Installs a given test."""
        timeout = self._resolve_timeout(timeout_sec)
        retries = "y\n" * 2 + "n\n"

        result = common_run_command(
            wrap_with_timeout(
                [self.name, "install", test_name],
                timeout,
                use_sudo=self.use_sudo,
            ),
            ssh_client=self.ssh_client,
            input_=retries,
        )
        if result.returncode:
            logger.error("Installation of PTS test %s failed. %s", test_name, result.stderr)
            return False

        result = self(["list-installed-tests"])
        if result.stdout.find(test_name) == -1:
            logger.error("Installation of PTS test %s failed. %s", test_name, result.stderr)
            return False
        logger.info("PTS test '%s' installed", test_name)
        return True

    def batch_run(
        self,
        test_name: str,
        iterations: int = 1,
        timeout_sec: int | None = None,
    ) -> ExecResult:
        timeout = self._resolve_timeout(timeout_sec)
        return common_run_command(
            self._batch_run_cmd(test_name, iterations, timeout),
            ssh_client=self.ssh_client,
        )

    def _resolve_timeout(self, timeout_sec: int | None) -> int:
        timeout = DEFAULT_TEST_TIMEOUT_SEC if timeout_sec is None else timeout_sec
        if timeout < 1:
            msg = "PTS test timeout must be greater than 0 seconds."
            raise ValueError(msg)
        return timeout

    def _batch_run_cmd(self, test_name: str, run_count: int, timeout_sec: int) -> list[str]:
        return wrap_with_timeout(
            [
                "env",
                f"FORCE_TIMES_TO_RUN={run_count}",
                self.name,
                "batch-run",
                test_name,
            ],
            timeout_sec,
            use_sudo=self.use_sudo,
        )

    @staticmethod
    def is_timeout_result(result: ExecResult) -> bool:
        return is_timeout_returncode(result.returncode) and any(
            line.lstrip().lower().startswith("timeout:") for line in result.stderr.splitlines()
        )

    @staticmethod
    def has_failed_runs(result: ExecResult) -> bool:
        return "The test quit with a non-zero exit status." in result.stdout

    @staticmethod
    def has_valid_metrics(  # noqa: PLR0911
        json_data: dict[str, Any] | None,
        *,
        allow_run_times: bool = False,
    ) -> bool:
        if json_data is None:
            return False

        test_results = json_data.get("results")
        if not isinstance(test_results, dict) or not test_results:
            return False

        for test_data in test_results.values():
            if not isinstance(test_data, dict):
                return False

            result_values = test_data.get("results")
            if not isinstance(result_values, dict) or not result_values:
                return False

            for result_value in result_values.values():
                if not isinstance(result_value, dict):
                    return False
                if result_value.get("value") is not None:
                    continue
                test_run_times = result_value.get("test_run_times")
                if allow_run_times and isinstance(test_run_times, list) and test_run_times:
                    continue
                return False

        return True

    @staticmethod
    def _failed_result(result: ExecResult, message: str) -> ExecResult:
        stderr = "\n".join(part for part in (result.stderr, message) if part)
        return ExecResult(
            cmd=result.cmd,
            stdout=result.stdout,
            stderr=stderr,
            returncode=1,
        )

    def _timeout_error(self, test_name: str, result: ExecResult, timeout_sec: int) -> None:
        if self.is_timeout_result(result):
            logger.error("PTS test '%s' timed out after %d seconds.", test_name, timeout_sec)

    def _run_appleseed(self, test_name: str, run_count: int, timeout_sec: int) -> ExecResult:
        return common_run_command(
            self._batch_run_cmd(test_name, run_count, timeout_sec),
            input_="4\n",
            ssh_client=self.ssh_client,
        )

    def _copy_latest_hdparm_result_home(self, test_name: str) -> None:
        last_result = self.get_latest_result_name()
        if last_result is None:
            return
        get_home_result = common_run_command(["echo", "$HOME"], self.ssh_client)
        if get_home_result.returncode:
            logger.warning("Failed to copy %s test results.", test_name)
        common_run_command(
            [
                *add_sudo(self.use_sudo),
                "mkdir",
                "-p",
                f"{get_home_result.stdout}/.{self.name}/test-results",
            ],
            ssh_client=self.ssh_client,
        )
        copy_result = common_run_command(
            [
                *add_sudo(self.use_sudo),
                "cp",
                "-r",
                f"/var/lib/{self.name}/test-results/{last_result}",
                f"{get_home_result.stdout}/.{self.name}/test-results/",
            ],
            ssh_client=self.ssh_client,
        )
        if copy_result.returncode:
            logger.warning("Failed to copy %s test results.", test_name)

    def remove_test(self, test_name: str) -> None:
        """Removes a given test."""
        commands = [["printf", "y\n"], [self.name, "remove-installed-test", test_name]]
        for result in pipeline(cmds=commands, ssh_client=self.ssh_client, pass_output=True):
            if result.returncode:
                logger.warning("Removal of PTS test '%s' failed", test_name)
                return
        logger.info("PTS test '%s' removed", test_name)

    def run_test(
        self,
        test_name: str,
        run_count: int,
        timeout_sec: int | None = None,
    ) -> ExecResult:
        """Runs a given test with set amount of iterations."""
        timeout = self._resolve_timeout(timeout_sec)
        ret = self.install_test(test_name, timeout_sec=timeout)
        if not ret:
            err_msg = f"Error installing PTS test: {test_name}"
            logger.error(err_msg)
            return ExecResult(cmd=(self.name, "install", test_name), stderr=err_msg, returncode=1)
        logger.info("PTS test '%s' started", test_name)
        if "pts/hdparm-read" in test_name:
            setup_answers = "y\n" + "n\n" * 6
            logger.info("Setting up PTS for %s test.", test_name)
            result = common_run_command(
                wrap_with_timeout(
                    [self.name, "batch-setup"],
                    timeout,
                    use_sudo=self.use_sudo,
                ),
                ssh_client=self.ssh_client,
                input_=setup_answers,
            )
            if result.returncode:
                logger.error("PTS setup failed: '%s'", result.stderr)
                return result
            result = self.batch_run(test_name, run_count, timeout)
            if result.returncode:
                self._timeout_error(test_name, result, timeout)
                logger.error("PTS test %s failed.", test_name)
                return result
            self._copy_latest_hdparm_result_home(test_name)
        elif "pts/appleseed" in test_name:
            result = self._run_appleseed(test_name, run_count, timeout)
        else:
            result = self.batch_run(test_name, run_count, timeout)
        if result.returncode:
            self._timeout_error(test_name, result, timeout)
            logger.warning("PTS test '%s' failed", test_name)
        else:
            logger.info("PTS test '%s' finished", test_name)
        return result

    def get_latest_result_name(self) -> str | None:
        """Returns latest result name.

        After setup() function, all results are saved in YYYY-MM-DD-HHMM format.

        Returns:
            Result name or None.
        """
        last_result = None
        for result in pipeline(
            [
                [*add_sudo(self.use_sudo), self.name, "list-results"],
                ["grep", "-oE", "'[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{4}'"],
                ["tail", "-1"],
            ],
            self.ssh_client,
            pass_output=True,
        ):
            if result.returncode:
                logger.warning("PTS results are missing")
                return None
            last_result = result
        return last_result.stdout.strip() if last_result is not None else None

    def get_result_json(self, result_name: str | None = None) -> dict[str, Any] | None:
        """Creates and returns a json file if result name exists.

        Args:
            result_name (str | None): Specific results or latest by default.

        Returns:
            dict[str, Any] json object with raw output or None if can't.
        """
        if result_name is None:
            latest_result_name = self.get_latest_result_name()
            if latest_result_name is None:
                return None
            result_name = latest_result_name

        result = self(["result-file-to-json", result_name])
        if result.returncode:
            return None
        path = SAVE_RESULT_PATH_PATTERN.search(result.stdout.strip())
        if path is None:
            return None
        result = common_run_command(
            [*add_sudo(self.use_sudo), "cat", path.group()],
            self.ssh_client,
        )
        if result.returncode:
            return None
        common_run_command([*add_sudo(self.use_sudo), "rm", "-f", path.group()], self.ssh_client)
        try:
            return json.loads(result.stdout)
        except Exception as e:
            error_message = "JSON parsing error"
            raise ValueError(error_message) from e

    @staticmethod
    def format_test_results(metrics: dict[str, Any]) -> str:
        """Format given metrics for readable output.

        Args:
            metrics (dict[str, Any]): Reduced and optimized JSON file.

        Returns:
            Readable results output in a form of string.
        """
        output: list[str] = []
        output.append("PTS test results")

        system = metrics.get("system_info", {})
        hardware = system.get("hardware", {})
        software = system.get("software", {})

        output.append("\nSystem info:")
        output.append(f"  Processor: {hardware.get('Processor', 'N/A')}")
        output.append(f"  Motherboard: {hardware.get('Motherboard', 'N/A')}")
        output.append(f"  Chipset: {hardware.get('Chipset', 'N/A')}")
        output.append(f"  Memory: {hardware.get('Memory', 'N/A')}")
        output.append(f"  Disk: {hardware.get('Disk', 'N/A')}")
        output.append(f"  OS: {software.get('OS', 'N/A')} ({software.get('Kernel', 'N/A')})")
        output.append(f"  File System: {software.get('File-System', 'N/A')}")
        output.append(f"  User: {system.get('user', {})}")

        total_tests = 0
        total_iterations = 0
        tests_time: dict[str, int] = {}

        output.append("\nTest results:")
        for test in metrics.get("results", []):
            total_tests += 1
            output.append(f"\n  Test: {test.get('title', 'N/A')}")
            output.append(f"    Description: {test.get('description')}")

            value = test.get("value", "N/A")
            scale = test.get("scale", "Milliseconds")
            output.append(f"    Average response time / Performance: {value} {scale}")

            test_run_times = test.get("test_run_times", [])

            output.append(f"    Amount of iterations: {len(test_run_times)}")
            for iteration, test_run_time in enumerate(test_run_times):
                total_iterations += 1
                output.append(f"      Iteration {iteration + 1}: {test_run_time} Seconds")
            output.append(f"    Total time: {sum(test_run_times)} Seconds")
            tests_time[test.get("title")] = sum(test_run_times)

        output.append("\nSummary:")
        output.append(f"  Total tests: {total_tests}")
        output.append(f"  Total iterations: {total_iterations}")
        output.append(f"  Total testing time: {sum(tests_time.values())} Seconds")

        for test, time in tests_time.items():
            output.append(f"    {test}: {time} Seconds")

        return "\n".join(output)

    @staticmethod
    def parse_metrics(json_data: dict[str, Any]) -> str:
        """Optimizes given JSON.

        Args:
            json_data (dict[str, Any]): Collected test results in form of JSON.

        Returns:
            Readable results output after formatting in a form of string.
        """
        metrics: dict[str, Any] = {"test_info": {}, "system_info": {}, "results": []}

        metrics["test_info"] = {
            "title": json_data.get("title", ""),
            "description": json_data.get("description", ""),
        }

        if "systems" in json_data:
            sys_info = json_data["systems"][next(iter(json_data["systems"]))]

            metrics["system_info"] = {
                "hardware": sys_info.get("hardware", {}),
                "software": sys_info.get("software", {}),
                "user": sys_info.get("user", ""),
            }

        if "results" in json_data:
            for test_id, test_data in json_data["results"].items():
                base_test_info = {
                    "id": test_id,
                    "identifier": test_data.get("identifier", ""),
                    "title": test_data.get("title", ""),
                    "description": test_data.get("description", ""),
                    "scale": test_data.get("scale", ""),
                }

                if "results" in test_data:
                    for result_id, result_value in test_data["results"].items():
                        test_result = {
                            **base_test_info,
                            "result_id": result_id,
                            "value": result_value.get("value"),
                            "test_run_times": result_value.get("test_run_times", []),
                        }

                        metrics["results"].append(test_result)

        return PhoronixTestSuite.format_test_results(metrics)

    def run(
        self,
        test_name: str,
        run_count: int,
        timeout_sec: int | None = None,
    ) -> tuple[ExecResult, dict[str, Any] | None]:
        """Runs a given test and parses results.

        Args:
            test_name (str): Name of PTS test.
            run_count (int): Amount of iterations of given test.
            timeout_sec (int | None): Test timeout in seconds. Uses 1 hour by default.

        Returns:
            tuple[ExecResult, dict[str, Any] | None]: Result of test and metrics.
        """
        result = self.run_test(test_name=test_name, run_count=run_count, timeout_sec=timeout_sec)
        if self.is_timeout_result(result) or result.returncode:
            return result, None
        json_data = self.get_result_json()
        allow_run_times = NETWORK_LOOPBACK_TEST_NAME in test_name
        has_valid_metrics = self.has_valid_metrics(
            json_data,
            allow_run_times=allow_run_times,
        )
        if (self.has_failed_runs(result) and not allow_run_times) or not has_valid_metrics:
            message = "PTS test completed without valid benchmark results."
            logger.warning("PTS test '%s' completed without valid benchmark results.", test_name)
            return self._failed_result(result, message), None
        return result, json_data

    def prepare(self, timeout_sec: int | None = None) -> ExecResult:
        """Prepares PTS for running tests.

        Sets up Google DNS server and turns off interactive questions in the future tests.
        """
        timeout = self._resolve_timeout(timeout_sec)
        setup_answers = "y\n" + "n\n" * 6

        dns_result = common_run_command(
            [*add_sudo(self.use_sudo), "tee", "-a", "/etc/resolv.conf"],
            ssh_client=self.ssh_client,
            input_="nameserver 8.8.8.8\n",
        )
        if dns_result.returncode:
            logger.warning("Failed to append Google DNS to /etc/resolv.conf")

        refresh_result = common_run_command(
            wrap_with_timeout(
                [self.name, "openbenchmarking-refresh"],
                timeout,
                use_sudo=self.use_sudo,
            ),
            ssh_client=self.ssh_client,
        )
        if refresh_result.returncode:
            logger.error("PTS openbenchmarking refresh failed: '%s'", refresh_result.stderr)
            return refresh_result

        setup_result = common_run_command(
            wrap_with_timeout(
                [self.name, "batch-setup"],
                timeout,
                use_sudo=self.use_sudo,
            ),
            ssh_client=self.ssh_client,
            input_=setup_answers,
        )
        if setup_result.returncode:
            logger.error("PTS setup failed: '%s'", setup_result.stderr)
            return setup_result
        logger.info("PTS setup successful")
        return setup_result

    @staticmethod
    def split_result(raw_metrics: dict[str, Any], test_index: int = 0) -> AdapterResult:
        if not raw_metrics:
            return AdapterResult(
                tool="pts",
                test_type={},
                time={},
                metrics={},
            )

        system_info = raw_metrics.get("systems", {})
        if system_info:
            system_info = system_info.get(next(iter(system_info.keys())), {})

        test_results = raw_metrics.get("results", {})
        if len(list(test_results.keys())) <= test_index:
            test_results = {}
        else:
            test_results = test_results.get(list(test_results.keys())[test_index], {})

        test_type = {
            "identifier": test_results.get("identifier", "unknown"),
        }
        time = {
            "timestamp": system_info.get("timestamp", "unknown"),
        }
        drop_json_fields(system_info, ["timestamp"])

        test_metrics = test_results.get("results", {})
        if test_metrics:
            test_metrics = {
                "systems": system_info,
                "results": test_metrics.get(next(iter(test_metrics.keys())), {}),
            }

        return AdapterResult(
            tool="pts",
            test_type=test_type,
            time=time,
            metrics=test_metrics,
        )
