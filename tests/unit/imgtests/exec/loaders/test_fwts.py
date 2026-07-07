from pathlib import Path
from textwrap import dedent
from typing import Final

import pytest

from imgtests.exec.loaders.fwts import Fwts, FwtsResult

FULL_OUTPUT: Final = (Path(__file__).parent / "data" / "fwts_out.txt").read_text()


@pytest.mark.parametrize(
    ("raw_output", "expected"),
    [
        (
            "",
            FwtsResult(
                tests=[],
                summary={"passed": 0, "failed": 0, "skipped": 0, "aborted": 0, "info": 0},
            ),
        ),
        (
            "Test: ACPI DSDT\n1 passed\n",
            FwtsResult(
                tests=[
                    {
                        "name": "ACPI DSDT",
                        "subtests": {
                            "passed": 1,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                ],
                summary={"passed": 1, "failed": 0, "skipped": 0, "aborted": 0, "info": 0},
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
                        "subtests": {
                            "passed": 2,
                            "failed": 1,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                ],
                summary={"passed": 2, "failed": 1, "skipped": 0, "aborted": 0, "info": 0},
            ),
        ),
        (
            "Test: MADT\nTest aborted\n",
            FwtsResult(
                tests=[
                    {
                        "name": "MADT",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 1,
                            "info": 0,
                        },
                    },
                ],
                summary={"passed": 0, "failed": 0, "skipped": 0, "aborted": 1, "info": 0},
            ),
        ),
        (
            "Test: MADT\nTest aborted.\n",
            FwtsResult(
                tests=[
                    {
                        "name": "MADT",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 1,
                            "info": 0,
                        },
                    },
                ],
                summary={"passed": 0, "failed": 0, "skipped": 0, "aborted": 1, "info": 0},
            ),
        ),
        (
            "Test: UEFI\nTest skipped\n",
            FwtsResult(
                tests=[
                    {
                        "name": "UEFI",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                ],
                summary={"passed": 0, "failed": 0, "skipped": 1, "aborted": 0, "info": 0},
            ),
        ),
        (
            "Test: UEFI\nTest skipped.\n",
            FwtsResult(
                tests=[
                    {
                        "name": "UEFI",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                ],
                summary={"passed": 0, "failed": 0, "skipped": 1, "aborted": 0, "info": 0},
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
                        "subtests": {
                            "passed": 3,
                            "failed": 1,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "KBD",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 2,
                            "aborted": 1,
                            "info": 0,
                        },
                    },
                ],
                summary={"passed": 3, "failed": 1, "skipped": 2, "aborted": 1, "info": 0},
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
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 3,
                        },
                    },
                ],
                summary={"passed": 0, "failed": 0, "skipped": 0, "aborted": 0, "info": 3},
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
                        "subtests": {
                            "passed": 2,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 1,
                        },
                    },
                ],
                summary={"passed": 2, "failed": 0, "skipped": 0, "aborted": 0, "info": 1},
            ),
        ),
        (
            "Test: HPET\n",
            FwtsResult(
                tests=[
                    {
                        "name": "HPET",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                ],
                summary={"passed": 0, "failed": 0, "skipped": 0, "aborted": 0, "info": 0},
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
                        "subtests": {
                            "passed": 5,
                            "failed": 0,
                            "skipped": 3,
                            "aborted": 1,
                            "info": 0,
                        },
                    },
                ],
                summary={"passed": 5, "failed": 0, "skipped": 3, "aborted": 1, "info": 0},
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
                        "subtests": {
                            "passed": 1,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "APIC",
                        "subtests": {
                            "passed": 2,
                            "failed": 1,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "MADT",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 1,
                            "info": 0,
                        },
                    },
                    {
                        "name": "UEFI",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "CPU",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 3,
                        },
                    },
                ],
                summary={"passed": 3, "failed": 1, "skipped": 1, "aborted": 1, "info": 3},
            ),
        ),
        (
            FULL_OUTPUT,
            FwtsResult(
                tests=[
                    {
                        "name": "Gather kernel system information",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 3,
                        },
                    },
                    {
                        "name": "Gather BIOS DMI information",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 1,
                        },
                    },
                    {
                        "name": "OPAL Processor Power Management DT Validation Tests",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "OPAL Reserved memory DT Validation Test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "OPAL Processor Recovery Diagnostics Info",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Scan kernel log for Oopses",
                        "subtests": {
                            "passed": 2,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Run OLOG scan and analysis checks",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Scan kernel log for errors and warnings",
                        "subtests": {
                            "passed": 0,
                            "failed": 3,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "BMC Info",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Scan coreboot log for errors and warnings",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "MTRR tests",
                        "subtests": {
                            "passed": 3,
                            "failed": 1,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "General ACPI information test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 3,
                        },
                    },
                    {
                        "name": "Base device tree validity check",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "OPAL CPU Info",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "OPAL MEM Info",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Sanity check for UEFI Boot Path Boot####",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 1,
                            "info": 0,
                        },
                    },
                    {
                        "name": "UEFI Compatibility Support Module test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 1,
                        },
                    },
                    {
                        "name": "Sanity check TPM event log",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Test firmware has set PCI Express MaxReadReq to a higher value on n",  # noqa: E501
                        "subtests": {
                            "passed": 1,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Test PCI host bridge configuration using _CRS",
                        "subtests": {
                            "passed": 1,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "PCIe ASPM test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "OPAL MTD Info",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "DMI/SMBIOS table tests",
                        "subtests": {
                            "passed": 16,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Test if system is using latest microcode",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "MSR register tests",
                        "subtests": {
                            "passed": 117,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Test if CPU NX is disabled by the BIOS",
                        "subtests": {
                            "passed": 3,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "CPU frequency scaling tests",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 1,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Test max CPU frequencies against max scaling frequency",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "CPU Virtualisation Configuration test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "SMM tests",
                        "subtests": {
                            "passed": 0,
                            "failed": 3,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "BIOS Support Installation structure test",
                        "subtests": {
                            "passed": 2,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "PCI IRQ Routing Table test",
                        "subtests": {
                            "passed": 4,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "MultiProcessor Tables tests",
                        "subtests": {
                            "passed": 9,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Interrupt tests",
                        "subtests": {
                            "passed": 1,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "HDA Audio Pin Configuration test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Test EBDA region is mapped and reserved in memory map table",
                        "subtests": {
                            "passed": 1,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "BIOS32 Service Directory test",
                        "subtests": {
                            "passed": 4,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "APIC edge/level test",
                        "subtests": {
                            "passed": 1,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "XENV Xen Environment Table tests",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "XSDT Extended System Description Table test",
                        "subtests": {
                            "passed": 1,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "WSMT Windows SMM Security Mitigations Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "WPBT Windows Platform Binary Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Extract and analyse Windows Management Instrumentation (WMI)",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "WDAT Microsoft Hardware Watchdog Action Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "ACPI Wakealarm tests",
                        "subtests": {
                            "passed": 6,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "WAET Windows ACPI Emulated Devices Table test",
                        "subtests": {
                            "passed": 1,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "ACPI Unique IDs test",
                        "subtests": {
                            "passed": 25,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "UEFI Data Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "TPM2 Trusted Platform Module 2 test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "TCPA Trusted Computing Platform Alliance Capabilities Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "SVKL Storage Volume Key Data table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "STAO Status Override Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "SRAT System Resource Affinity Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "SPMI Service Processor Management Interface Description Table test",  # noqa: E501
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "SPCR Serial Port Console Redirection Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "SLIT System Locality Distance Information test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "SLIC Software Licensing Description Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "SDEV Secure Devices Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "SDEI Software Delegated Exception Interface Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "SBST Smart Battery Specification Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "RSDT Root System Description Table test",
                        "subtests": {
                            "passed": 1,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "RSDP Root System Description Pointer test",
                        "subtests": {
                            "passed": 8,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "RGRT Regulatory Graphics Resource Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "RASF RAS Feature Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "PPTT Processor Properties Topology Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "PMTT Memory Topology Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "PHAT Platform Health Assessment Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "PDTT Platform Debug Trigger Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "PCCT Platform Communications Channel test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Processor Clocking Control (PCC) test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 1,
                        },
                    },
                    {
                        "name": 'Disassemble DSDT to check for _OSI("Linux")',
                        "subtests": {
                            "passed": 1,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "NFIT NVDIMM Firmware Interface Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "ACPI DSDT Method Semantic tests",
                        "subtests": {
                            "passed": 164,
                            "failed": 0,
                            "skipped": 209,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "MSDM Microsoft Data Management Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "MSCT Maximum System Characteristics Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "MPST Memory Power State Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "MCHI Management Controller Host Interface Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "MCFG PCI Express* memory mapped config space test",
                        "subtests": {
                            "passed": 2,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "MADT Multiple APIC Description Table (spec compliant)",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 1,
                            "info": 0,
                        },
                    },
                    {
                        "name": "LPIT Low Power Idle Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "IORT IO Remapping Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "HMAT Heterogeneous Memory Attribute Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "HPET IA-PC High Precision Event Timer Table tests",
                        "subtests": {
                            "passed": 5,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "HEST Hardware Error Source Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "GTDT Generic Timer Description Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "FPDT Firmware Performance Data Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Simple fan tests",
                        "subtests": {
                            "passed": 4,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "FADT Fixed ACPI Description Table tests",
                        "subtests": {
                            "passed": 29,
                            "failed": 1,
                            "skipped": 3,
                            "aborted": 0,
                            "info": 1,
                        },
                    },
                    {
                        "name": "FACS Firmware ACPI Control Structure test",
                        "subtests": {
                            "passed": 1,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "ERST Error Record Serialization Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "EINJ Error Injection Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "ECDT Embedded Controller Boot Resources Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "DRTM D-RTM Resources Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "DPPT DMA Protection Policy Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "DMA Remapping (VT-d) test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Wireless power calibration device test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Time and alarm device test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Ambient light sensor device test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "NVDIMM device test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Lid device test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Sleep button device test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Power button device test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "ACPI embedded controller device test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "ACPI smart battery device test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "ACPI battery device test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "AC adapter device test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "DBG2 (Debug Port Table 2) test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "DBGP (Debug Port) Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Processor C state support test",
                        "subtests": {
                            "passed": 7,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "CSRT Core System Resource Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "CPEP Corrected Platform Error Polling Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "ACPI table checksum test",
                        "subtests": {
                            "passed": 10,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "CEDT CXL Early Discovery Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Automated LCD brightness test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 1,
                            "info": 0,
                        },
                    },
                    {
                        "name": "BOOT Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "BGRT Boot Graphics Resource Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "BERT Boot Error Record Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "ASPT Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "ASF! Alert Standard Format Table test",
                        "subtests": {
                            "passed": 0,
                            "failed": 0,
                            "skipped": 1,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "Test for single instance of APIC/MADT table",
                        "subtests": {
                            "passed": 1,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                    {
                        "name": "ACPI table headers sanity tests",
                        "subtests": {
                            "passed": 8,
                            "failed": 0,
                            "skipped": 0,
                            "aborted": 0,
                            "info": 0,
                        },
                    },
                ],
                summary={"passed": 439, "failed": 8, "skipped": 291, "aborted": 4, "info": 10},
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
        "full fwts output",
    ],
)
def test_parse_metrics(raw_output: str, expected: FwtsResult) -> None:
    result = Fwts.parse_metrics(raw_output)
    assert result == expected
