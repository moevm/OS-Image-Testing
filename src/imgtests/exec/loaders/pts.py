import json
import logging
from pathlib import Path
from typing import Any

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import SSHClient
from imgtests.logger import set_handlers

logger = logging.getLogger(__name__)
set_handlers(logger, Path("processing.log"))


class PhoronixTestSuite(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("phoronix-test-suite", ssh_client)

    def setup(self) -> None:
        """Prepares PTS for running tests.

        Sets up Google DNS server and turns off interactive questions in the future tests.
        """
        self.ssh_client('echo "nameserver 8.8.8.8" > /etc/resolv.conf')
        setup_answers = "y\n" + "n\n" * 6
        result = self.ssh_client(f"printf '{setup_answers}' | phoronix-test-suite batch-setup")
        if result.returncode == 0:
            logger.info("PTS setup successful")
        else:
            logger.warning("PTS setup failed: '%s'", result.stderr)

    def install_test(self, test_name: str) -> None:
        """Installs a given test in the ssh client."""
        result = self.ssh_client(f"phoronix-test-suite install {test_name}")
        if result.returncode == 0:
            logger.info("PTS test '%s' installed", test_name)
        else:
            logger.warning("Installation of PTS test '%s' failed", test_name)

    def run_test(self, test_name: str, run_count: int) -> None:
        """Runs a given test with set amount of iterations in the ssh client."""
        self.install_test(test_name=test_name)
        result = self.ssh_client(
            f"FORCE_TIMES_TO_RUN={run_count} phoronix-test-suite batch-run {test_name}"
        )
        if result.returncode == 0:
            logger.info("PTS test '%s' finished", test_name)
        else:
            logger.warning("PTS test '%s' failed", test_name)

    def get_latest_result_name(self) -> str | None:
        """Returns latest result name.

        After setup() function, all results are saved in YYYY-MM-DD-HHMM format.

        Returns:
            Result name or None.
        """
        result_name = self.ssh_client(
            "phoronix-test-suite list-results | "
            "grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{4}' | "
            "tail -1"
        )
        if result_name.returncode == 0 and result_name.stdout.strip():
            return result_name.stdout.strip()
        logger.warning("PTS results are missing")
        return None

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

        self.ssh_client(f"phoronix-test-suite result-file-to-json {result_name}")

        result = self.ssh_client(f"cat {result_name}.json")

        self.ssh_client(f"rm {result_name}.json")

        try:
            return json.loads(result.stdout)
        except Exception as e:
            error_message = "JSON parsing error"
            raise ValueError(error_message) from e

    def format_test_results(self, metrics: dict[str, Any]) -> str:
        """Format given metrics for readable output.

        Args:
            metrics (dict[str, Any]): Reduced and optimized JSON file.

        Returns:
            Readable results output in a form of string.
        """
        output = []
        output.append("PTS Test results")

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
        tests_time = {}

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

    def parse_metrics(self, json_data: dict[str, Any]) -> str:
        """Optimizes given JSON.

        Args:
            json_data (dict[str, Any]): Collected test results in form of JSON.

        Returns:
            Readable results output after formatting in a form of string.
        """
        metrics = {"test_info": {}, "system_info": {}, "results": []}

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

        return self.format_test_results(metrics)

    def run(self, test_name: str, run_count: int) -> str:
        """Runs a given test and parses results.

        Args:
            test_name (str): Name of PTS test.
            run_count (int): Amount of iterations of given test.

        Returns:
            Formatted readable output.
        """
        self.run_test(test_name=test_name, run_count=run_count)

        try:
            json_data = self.get_result_json()
        except ValueError as e:
            return f"Error while processing results: {e}"
        return self.parse_metrics(json_data)
