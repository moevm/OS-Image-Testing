from textwrap import dedent

import pytest

from imgtests.exec.loaders.fwts import Fwts, FwtsResult


@pytest.mark.parametrize(
    ("raw_output", "expected"),
    [
        (
            "",
            FwtsResult(
                tests=[],
                summary={"passed": 0, "failed": 0, "skipped": 0, "aborted": 0},
            ),
        ),
        (
            "Test: ACPI DSDT\n1 passed\n",
            FwtsResult(
                tests=[
                    {
                        "name": "ACPI DSDT",
                        "subtests": {"passed": 1, "failed": 0, "skipped": 0, "aborted": 0},
                    },
                ],
                summary={"passed": 1, "failed": 0, "skipped": 0, "aborted": 0},
            ),
        ),
        (
            dedent("""\
                Test: APIC
                2 passed
                1 failed
                """),
            FwtsResult(
                tests=[
                    {
                        "name": "APIC",
                        "subtests": {"passed": 2, "failed": 1, "skipped": 0, "aborted": 0},
                    },
                ],
                summary={"passed": 2, "failed": 1, "skipped": 0, "aborted": 0},
            ),
        ),
        (
            "Test: MADT\nTest aborted\n",
            FwtsResult(
                tests=[
                    {
                        "name": "MADT",
                        "subtests": {"passed": 0, "failed": 0, "skipped": 0, "aborted": 1},
                    },
                ],
                summary={"passed": 0, "failed": 0, "skipped": 0, "aborted": 1},
            ),
        ),
        (
            "Test: MADT\nTest aborted.\n",
            FwtsResult(
                tests=[
                    {
                        "name": "MADT",
                        "subtests": {"passed": 0, "failed": 0, "skipped": 0, "aborted": 1},
                    },
                ],
                summary={"passed": 0, "failed": 0, "skipped": 0, "aborted": 1},
            ),
        ),
        (
            "Test: UEFI\nTest skipped\n",
            FwtsResult(
                tests=[
                    {
                        "name": "UEFI",
                        "subtests": {"passed": 0, "failed": 0, "skipped": 1, "aborted": 0},
                    },
                ],
                summary={"passed": 0, "failed": 0, "skipped": 1, "aborted": 0},
            ),
        ),
        (
            "Test: UEFI\nTest skipped.\n",
            FwtsResult(
                tests=[
                    {
                        "name": "UEFI",
                        "subtests": {"passed": 0, "failed": 0, "skipped": 1, "aborted": 0},
                    },
                ],
                summary={"passed": 0, "failed": 0, "skipped": 1, "aborted": 0},
            ),
        ),
        (
            dedent("""\
                Test: SBDR
                3 passed
                1 failed
                Test: KBD
                2 skipped
                Test aborted
                """),
            FwtsResult(
                tests=[
                    {
                        "name": "SBDR",
                        "subtests": {"passed": 3, "failed": 1, "skipped": 0, "aborted": 0},
                    },
                    {
                        "name": "KBD",
                        "subtests": {"passed": 0, "failed": 0, "skipped": 2, "aborted": 1},
                    },
                ],
                summary={"passed": 3, "failed": 1, "skipped": 2, "aborted": 1},
            ),
        ),
        (
            dedent("""\
                Test: CPU
                3 info only
                """),
            FwtsResult(
                tests=[
                    {
                        "name": "CPU",
                        "subtests": {"passed": 3, "failed": 0, "skipped": 0, "aborted": 0},
                    },
                ],
                summary={"passed": 3, "failed": 0, "skipped": 0, "aborted": 0},
            ),
        ),
        (
            dedent("""\
                Test: MCHV
                2 passed
                1 info only
                """),
            FwtsResult(
                tests=[
                    {
                        "name": "MCHV",
                        "subtests": {"passed": 3, "failed": 0, "skipped": 0, "aborted": 0},
                    },
                ],
                summary={"passed": 3, "failed": 0, "skipped": 0, "aborted": 0},
            ),
        ),
        (
            "Test: HPET\n",
            FwtsResult(
                tests=[
                    {
                        "name": "HPET",
                        "subtests": {"passed": 0, "failed": 0, "skipped": 1, "aborted": 0},
                    },
                ],
                summary={"passed": 0, "failed": 0, "skipped": 1, "aborted": 0},
            ),
        ),
        (
            dedent("""\
                Test: FAN
                5 passed
                0 failed
                3 skipped
                1 aborted
                """),
            FwtsResult(
                tests=[
                    {
                        "name": "FAN",
                        "subtests": {"passed": 5, "failed": 0, "skipped": 3, "aborted": 1},
                    },
                ],
                summary={"passed": 5, "failed": 0, "skipped": 3, "aborted": 1},
            ),
        ),
        (
            dedent("""\
                Test: ACPI DSDT
                1 passed
                Test: APIC
                2 passed
                1 failed
                Test: MADT
                Test aborted
                Test: UEFI
                Test skipped
                Test: CPU
                3 info only
                """),
            FwtsResult(
                tests=[
                    {
                        "name": "ACPI DSDT",
                        "subtests": {"passed": 1, "failed": 0, "skipped": 0, "aborted": 0},
                    },
                    {
                        "name": "APIC",
                        "subtests": {"passed": 2, "failed": 1, "skipped": 0, "aborted": 0},
                    },
                    {
                        "name": "MADT",
                        "subtests": {"passed": 0, "failed": 0, "skipped": 0, "aborted": 1},
                    },
                    {
                        "name": "UEFI",
                        "subtests": {"passed": 0, "failed": 0, "skipped": 1, "aborted": 0},
                    },
                    {
                        "name": "CPU",
                        "subtests": {"passed": 3, "failed": 0, "skipped": 0, "aborted": 0},
                    },
                ],
                summary={"passed": 6, "failed": 1, "skipped": 1, "aborted": 1},
            ),
        ),
    ],
    ids=[
        "empty_output",
        "one_test_all_passed",
        "one_test_mix_pass_fail",
        "test_aborted_without_dot",
        "test_aborted_with_dot",
        "test_skipped_without_dot",
        "test_skipped_with_dot",
        "multiple_tests_mixed_status",
        "all_info_only",
        "passed_and_info_only",
        "no_subresults_skipped",
        "all_counters_nonzero",
        "complex",
    ],
)
def test_parse_metrics(raw_output: str, expected: FwtsResult) -> None:
    result = Fwts.parse_metrics(raw_output)
    assert result == expected
