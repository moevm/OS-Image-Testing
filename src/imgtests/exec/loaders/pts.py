import json
import logging
from typing import TYPE_CHECKING, Any

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient, common_run_command, pipeline
from imgtests.exec.utils import extract_version

if TYPE_CHECKING:
    from imgtests.types import Version

logger = logging.getLogger(__name__)


class PhoronixTestSuite(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("phoronix-test-suite", ssh_client)

    def version(self) -> Version | None:
        result = self(["version"])
        if result.returncode:
            return None
        return extract_version(result.stdout.strip())

    def install_test(self, test_name: str) -> bool:
        """Installs a given test."""
        retries = "y\n" * 2 + "n\n"
        commands = [["echo", "-e", f'"{retries}"'], ["phoronix-test-suite", "install", test_name]]
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

    def remove_test(self, test_name: str) -> None:
        """Removes a given test."""
        commands = [["printf", "y\n"], [self.name, "remove-installed-test", test_name]]
        for result in pipeline(cmds=commands, ssh_client=self.ssh_client, pass_output=True):
            if result.returncode:
                logger.warning("Removal of PTS test '%s' failed", test_name)
                return
        logger.info("PTS test '%s' removed", test_name)

    def run_test(self, test_name: str, run_count: int) -> ExecResult | None:
        """Runs a given test with set amount of iterations."""
        if not self.install_test(test_name=test_name):
            return None
        logger.info("PTS test '%s' started", test_name)
        result = common_run_command(
            [f"FORCE_TIMES_TO_RUN={run_count}", self.name, "batch-run", test_name],
            ssh_client=self.ssh_client,
        )
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
                [self.name, "list-results"],
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

    def get_result_json(self, result_name: str | None = None) -> dict[str, Any]:
        """Creates and returns a json file if result name exists.

        Args:
            result_name (str | None): Specific results or latest by default.

        Raises:
            ValueError: When there are no test results or JSON is corrupted.

        Returns:
            JSON file with raw output.
        """
        if result_name is None:
            latest_result_name = self.get_latest_result_name()
            if latest_result_name is None:
                error_message = "Test results are missing"
                raise ValueError(error_message)
            result_name = latest_result_name

        self(["result-file-to-json", result_name])
        result = common_run_command(["cat", f"{result_name}.json"], self.ssh_client)
        common_run_command(["rm", "-f", f"{result_name}.json"], self.ssh_client)
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

    def run(self, test_name: str, run_count: int) -> tuple[ExecResult, dict[str, Any]]:
        """Runs a given test and parses results.

        Args:
            test_name (str): Name of PTS test.
            run_count (int): Amount of iterations of given test.

        Returns:
            Returns:
            tuple[ExecResult, dict[str, Any]]: Result of test and metrics.
        """
        result = self.run_test(test_name=test_name, run_count=run_count)

        try:
            json_data = self.get_result_json()
        except ValueError as e:
            return f"Error while processing results: {e}"
        return result, json_data

    @staticmethod
    def serialize_metrics(result: dict[str, Any]) -> str:
        return json.dumps(result)


def setup_pts(ssh_client: SSHClient | None = None) -> None:
    """Prepares PTS for running tests.

    Sets up Google DNS server and turns off interactive questions in the future tests.
    """
    result = common_run_command(
        cmd=["echo", "'nameserver 8.8.8.8'", ">", "/etc/resolv.conf"],
        ssh_client=ssh_client,
    )
    if result.returncode:
        logger.error("PTS setup failed: '%s'", result.stderr)
        return

    common_run_command(
        cmd=["phoronix-test-suite", "openbenchmarking-refresh"],
        ssh_client=ssh_client,
    )

    setup_answers = "y\n" + "n\n" * 6
    commands = [["echo", "-e", f'"{setup_answers}"'], ["phoronix-test-suite", "batch-setup"]]
    for result in pipeline(cmds=commands, ssh_client=ssh_client, pass_output=True):
        if result.returncode:
            logger.error("PTS setup failed: '%s'", result.stderr)
            return
    logger.info("PTS setup successful")
