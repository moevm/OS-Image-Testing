import json
import logging
import re
from typing import TYPE_CHECKING, Any

from imgtests.adapter import JSONAdapter
from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient, common_run_command, pipeline
from imgtests.exec.pkgmgrs.mixin import PkgMgrMixin
from imgtests.exec.utils import add_sudo, extract_version

if TYPE_CHECKING:
    from imgtests.types import Version


SAVE_RESULT_PATH_PATTERN = re.compile("/[^:]*")

logger = logging.getLogger(__name__)


class PhoronixTestSuite(PkgMgrMixin, GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None, use_sudo: bool = True) -> None:
        super().__init__("phoronix-test-suite", ssh_client, use_sudo=use_sudo)

    def install(self) -> ExecResult:
        """Install phoronix-test-suite via the system package manager."""
        if self.path:
            return ExecResult(
                cmd=(), stderr=f"{self.name} already has been installed.", returncode=0
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

    def install_test(self, test_name: str) -> bool:
        """Installs a given test."""
        retries = "y\n" * 2 + "n\n"
        commands: list[list[str]] = [
            ["echo", "-e", f'"{retries}"'],
            [*add_sudo(self.use_sudo), self.name, "install", test_name],
        ]
        for result in pipeline(cmds=commands, ssh_client=self.ssh_client, pass_output=True):
            if result.returncode:
                logger.error("Installation of PTS test %s failed. %s", test_name, result.stderr)
                return False

        result = self(["list-installed-tests"])
        if result.stdout.find(test_name) == -1:
            logger.error("Installation of PTS test %s failed. %s", test_name, result.stderr)
            return False
        logger.info("PTS test '%s' installed", test_name)
        return True

    def batch_run(self, test_name: str, iterations: int = 1) -> ExecResult:
        return common_run_command(
            [
                *add_sudo(self.use_sudo),
                f"FORCE_TIMES_TO_RUN={iterations}",
                self.name,
                "batch-run",
                test_name,
            ],
            ssh_client=self.ssh_client,
        )

    def remove_test(self, test_name: str) -> None:
        """Removes a given test."""
        commands = [["printf", "y\n"], [self.name, "remove-installed-test", test_name]]
        for result in pipeline(cmds=commands, ssh_client=self.ssh_client, pass_output=True):
            if result.returncode:
                logger.warning("Removal of PTS test '%s' failed", test_name)
                return
        logger.info("PTS test '%s' removed", test_name)

    def run_test(self, test_name: str, run_count: int) -> ExecResult:
        """Runs a given test with set amount of iterations."""
        ret = self.install_test(test_name)
        if not ret:
            logger.error("Error installing PTS test: %s", test_name)
        logger.info("PTS test '%s' started", test_name)
        if "pts/hdparm-read" in test_name:
            setup_answers = "y\n" + "n\n" * 6
            commands = [
                ["echo", "-e", f'"{setup_answers}"'],
                [*add_sudo(self.use_sudo), self.name, "batch-setup"],
            ]
            logger.info("Setting up PTS for %s test.", test_name)
            for result in pipeline(cmds=commands, ssh_client=self.ssh_client, pass_output=True):
                if result.returncode:
                    logger.error("PTS setup failed: '%s'", result.stderr)
                    return result
            result = self.batch_run(test_name, run_count)
            if result.returncode:
                logger.error("PTS test %s failed.", test_name)
                return result
            last_result = self.get_latest_result_name()
            if last_result is not None:
                get_home_result = common_run_command(["echo", "$HOME"])
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
        elif "pts/appleseed" in test_name:
            result = common_run_command(
                [
                    "echo",
                    "4",
                    "|",
                    f"FORCE_TIMES_TO_RUN={run_count}",
                    self.name,
                    "batch-run",
                    test_name,
                ],
                ssh_client=self.ssh_client,
            )
        else:
            result = self.batch_run(test_name, run_count)
        if result.returncode:
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
            [*add_sudo(self.use_sudo), "cat", path.group()], self.ssh_client
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

    def run(self, test_name: str, run_count: int) -> tuple[ExecResult, dict[str, Any] | None]:
        """Runs a given test and parses results.

        Args:
            test_name (str): Name of PTS test.
            run_count (int): Amount of iterations of given test.

        Returns:
            tuple[ExecResult, dict[str, Any] | None]: Result of test and metrics.
        """
        result = self.run_test(test_name=test_name, run_count=run_count)
        json_data = self.get_result_json()
        return result, json_data

    def prepare(self) -> ExecResult:
        """Prepares PTS for running tests.

        Sets up Google DNS server and turns off interactive questions in the future tests.
        """
        setup_answers = "y\n" + "n\n" * 6
        commands = [
            [
                "echo",
                "'nameserver 8.8.8.8'",
                "|",
                "sudo",
                "tee",
                "-a",
                "/etc/resolv.conf",
                ">",
                "/dev/null",
            ],
            [self.name, "openbenchmarking-refresh"],
            ["echo", "-e", f'"{setup_answers}"'],
            [self.name, "batch-setup"],
        ]
        for result in pipeline(cmds=commands, ssh_client=self.ssh_client, pass_output=True):
            if result.returncode:
                logger.error("PTS setup failed: '%s'", result.stderr)
                return result
        logger.info("PTS setup successful")
        return result


class PhoronixTestSuiteAdapter(JSONAdapter):
    def __init__(self) -> None:
        self.tool = "pts"

    def split_result(self, raw_result: dict[str, Any], test_index: int = 0) -> dict[str, Any]:
        system_info = raw_result.get("systems", {})
        system_info = system_info.get(next(iter(system_info.keys())), {})

        test_results = raw_result.get("results", {})
        test_results = test_results.get(list(test_results.keys())[test_index], {})

        test_metrics = test_results.get("results", {})
        test_metrics = test_metrics.get(next(iter(test_metrics.keys())), {})
        test_metrics = self.drop_fields(test_metrics, ["details"])

        test_type = {
            "identifier": test_results.get("identifier", ""),
            "title": test_results.get("title", ""),
            "description": test_results.get("description", ""),
        }
        time = {
            "timestamp": system_info.get("timestamp", ""),
        }

        return {
            "test_type": test_type,
            "time": time,
            "metrics": test_metrics,
            "summary": {},
        }
