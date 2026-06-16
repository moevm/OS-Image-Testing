import logging
import re
from typing import TYPE_CHECKING, Any, NamedTuple

from imgtests.exec.base_util import GenericUtil
from imgtests.results_adapter import AdapterResult
from imgtests.types import MetricSample

if TYPE_CHECKING:
    from imgtests.exec.exec import ExecResult, SSHClient

logger = logging.getLogger(__name__)


class FwtsResult(NamedTuple):
    tests: list[dict[str, Any]]
    summary: dict[str, int]


class Fwts(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("fwts", ssh_client)

    def run(self) -> tuple[ExecResult, FwtsResult]:
        result = self()
        parsed = (
            self.parse_metrics(result.stdout)
            if result.stdout
            else FwtsResult(
                tests=[],
                summary={"passed": 0, "failed": 0, "skipped": 0, "aborted": 0},
            )
        )
        return result, parsed

    @staticmethod
    def parse_metrics(raw_output: str) -> FwtsResult:
        statuses: dict[str, int] = {"passed": 0, "failed": 0, "skipped": 0, "aborted": 0}
        tests: list[dict[str, Any]] = []

        sections = re.split(r"^Test: ", raw_output, flags=re.MULTILINE)

        for section in sections[1:]:
            lines = section.splitlines()
            test_name = lines[0].strip().rstrip(".")
            subtotal: dict[str, int] = {"passed": 0, "failed": 0, "skipped": 0, "aborted": 0}

            for line in lines[1:]:
                stripped = line.strip()

                if stripped in ("Test aborted", "Test aborted."):
                    subtotal["aborted"] += 1
                elif stripped in ("Test skipped", "Test skipped."):
                    subtotal["skipped"] += 1
                else:
                    for match in re.finditer(
                        r"(\d+)\s+(passed|failed|skipped|aborted|info only)",
                        stripped.lower(),
                    ):
                        count = int(match.group(1))
                        status = match.group(2)
                        if status == "info only":
                            statuses["passed"] += count
                            subtotal["passed"] += count
                        elif status in subtotal:
                            subtotal[status] += count

            if all(v == 0 for v in subtotal.values()):
                subtotal["skipped"] += 1

            for key, value in subtotal.items():
                statuses[key] += value
            tests.append({"name": test_name, "subtests": subtotal})

        return FwtsResult(tests=tests, summary=statuses)

    @staticmethod
    def metrics_to_json(metrics: FwtsResult) -> dict[str, Any]:
        raw = {"fwts_tests": metrics.tests, "fwts_summary": metrics.summary}
        return Fwts.split_result(raw_metrics=raw)

    @staticmethod
    def split_result(raw_metrics: dict[str, Any]) -> AdapterResult:
        if not raw_metrics:
            return AdapterResult(tool="fwts", test_type={}, time={}, metrics={})

        tests = raw_metrics.get("fwts_tests", [])
        summary = raw_metrics.get("fwts_summary", {})

        test_type = {"type": "firmware"}
        time = {}
        metrics: dict[str, Any] = {str(i): t for i, t in enumerate(tests)}
        metrics["summary"] = summary

        return AdapterResult(tool="fwts", test_type=test_type, time=time, metrics=metrics)


def fwts_metrics_to_samples(
    stage_name: str,
    subsystem: str,
    metrics: dict[str, Any],
) -> list[MetricSample]:
    samples: list[MetricSample] = []
    summary = metrics.get("summary", {})
    for key, label in (
        ("passed", "Passed"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
        ("aborted", "Aborted"),
    ):
        value = summary.get(key, 0)
        samples.append(
            MetricSample(stage_name, subsystem, f"fwts.{key}", float(value), label=label),
        )
    return samples
