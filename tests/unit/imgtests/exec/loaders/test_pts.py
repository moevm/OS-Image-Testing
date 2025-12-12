from typing import Any

import pytest

from imgtests.exec.loaders.pts import PhoronixTestSuite


@pytest.mark.parametrize(
    ("raw_metrics", "expected"),
    [
        (
            {
                "title": "2025-12-12-2222",
                "last_modified": "2025-12-12 22:30:58",
                "description": "Intel Xeon E3-12xx v2 testing with a QEMU Standard PC (Q35 + ICH9 2009) (rel-1.16.3-0-ga6ed6b701f0a-prebuilt.qemu.org BIOS) and bochs-drmdrmfb on poky 5.2.4 via the Phoronix Test Suite.",
                "systems": {
                    "2025-12-12 22:22": {
                        "identifier": "2025-12-12 22:22",
                        "hardware": {
                            "Processor": "Intel Xeon E3-12xx v2 (4 Cores)",
                            "Motherboard": "QEMU Standard PC (Q35 + ICH9 2009) (rel-1.16.3-0-ga6ed6b701f0a-prebuilt.qemu.org BIOS)",
                            "Chipset": "Intel 82G33/G31/P35/P31 + ICH9",
                            "Memory": "1 x 2 GB RAM QEMU",
                            "Disk": "10GB",
                            "Graphics": "bochs-drmdrmfb",
                            "Monitor": "QEMU Monitor",
                            "Network": "Red Hat Virtio device",
                        },
                        "software": {
                            "OS": "poky 5.2.4",
                            "Kernel": "6.12.47-yocto-standard (x86_64)",
                            "Compiler": "GCC 14.3.0",
                            "File-System": "ext4",
                            "Screen Resolution": "1280x800",
                        },
                        "user": "root",
                        "timestamp": "2025-12-12 22:22:33",
                        "client_version": "10.8.4",
                        "data": {
                            "cpu-microcode": "0x1",
                            "python": "Python 3.13.4",
                            "security": "gather_data_sampling: Not affected + indirect_target_selection: Mitigation of Aligned branch/return thunks + itlb_multihit: vulnerable + l1tf: Mitigation of PTE Inversion + mds: Vulnerable: Clear buffers attempted no microcode; SMT Host state unknown + meltdown: Mitigation of PTI + mmio_stale_data: Unknown: No mitigations + reg_file_data_sampling: Not affected + retbleed: Not affected + spec_rstack_overflow: Not affected + spec_store_bypass: Vulnerable + spectre_v1: Mitigation of usercopy/swapgs barriers and __user pointer sanitization + spectre_v2: Mitigation of Retpolines; STIBP: disabled; RSB filling; PBRSB-eIBRS: Not affected; BHI: Retpoline + srbds: Unknown: Dependent on hypervisor status + tsa: Not affected + tsx_async_abort: Not affected + vmscape: Not affected",
                        },
                    }
                },
                "results": {
                    "fa95c59f61f38f7b8191e913fa323e51b9368538": {
                        "identifier": "pts/pybench-1.1.3",
                        "title": "PyBench",
                        "app_version": "2018-02-16",
                        "description": "Total For Average Test Times",
                        "scale": "Milliseconds",
                        "proportion": "LIB",
                        "display_format": "BAR_GRAPH",
                        "results": {},
                    }
                },
            },
            (
                "PTS test results\n\n"
                "System info:\n"
                "  Processor: Intel Xeon E3-12xx v2 (4 Cores)\n"
                "  Motherboard: QEMU Standard PC (Q35 + ICH9 2009) (rel-1.16.3-0-ga6ed6b701f0a-prebuilt.qemu.org BIOS)\n"
                "  Chipset: Intel 82G33/G31/P35/P31 + ICH9\n"
                "  Memory: 1 x 2 GB RAM QEMU\n"
                "  Disk: 10GB\n"
                "  OS: poky 5.2.4 (6.12.47-yocto-standard (x86_64))\n"
                "  File System: ext4\n"
                "  User: root\n\n"
                "Test results:\n\n"
                "Summary:\n"
                "  Total tests: 0\n"
                "  Total iterations: 0\n"
                "  Total testing time: 0 Seconds"
            ),
        ),
        (
            {
                "title": "2025-12-12-2222",
                "last_modified": "2025-12-12 22:30:58",
                "description": "Intel Xeon E3-12xx v2 testing with a QEMU Standard PC (Q35 + ICH9 2009) (rel-1.16.3-0-ga6ed6b701f0a-prebuilt.qemu.org BIOS) and bochs-drmdrmfb on poky 5.2.4 via the Phoronix Test Suite.",
                "systems": {
                    "2025-12-12 22:22": {
                        "identifier": "2025-12-12 22:22",
                        "hardware": {
                            "Processor": "Intel Xeon E3-12xx v2 (4 Cores)",
                            "Motherboard": "QEMU Standard PC (Q35 + ICH9 2009) (rel-1.16.3-0-ga6ed6b701f0a-prebuilt.qemu.org BIOS)",
                            "Chipset": "Intel 82G33/G31/P35/P31 + ICH9",
                            "Memory": "1 x 2 GB RAM QEMU",
                            "Disk": "10GB",
                            "Graphics": "bochs-drmdrmfb",
                            "Monitor": "QEMU Monitor",
                            "Network": "Red Hat Virtio device",
                        },
                        "software": {
                            "OS": "poky 5.2.4",
                            "Kernel": "6.12.47-yocto-standard (x86_64)",
                            "Compiler": "GCC 14.3.0",
                            "File-System": "ext4",
                            "Screen Resolution": "1280x800",
                        },
                        "user": "root",
                        "timestamp": "2025-12-12 22:22:33",
                        "client_version": "10.8.4",
                        "data": {
                            "cpu-microcode": "0x1",
                            "python": "Python 3.13.4",
                            "security": "gather_data_sampling: Not affected + indirect_target_selection: Mitigation of Aligned branch/return thunks + itlb_multihit: vulnerable + l1tf: Mitigation of PTE Inversion + mds: Vulnerable: Clear buffers attempted no microcode; SMT Host state unknown + meltdown: Mitigation of PTI + mmio_stale_data: Unknown: No mitigations + reg_file_data_sampling: Not affected + retbleed: Not affected + spec_rstack_overflow: Not affected + spec_store_bypass: Vulnerable + spectre_v1: Mitigation of usercopy/swapgs barriers and __user pointer sanitization + spectre_v2: Mitigation of Retpolines; STIBP: disabled; RSB filling; PBRSB-eIBRS: Not affected; BHI: Retpoline + srbds: Unknown: Dependent on hypervisor status + tsa: Not affected + tsx_async_abort: Not affected + vmscape: Not affected",
                        },
                    }
                },
                "results": {
                    "fa95c59f61f38f7b8191e913fa323e51b9368538": {
                        "identifier": "pts/pybench-1.1.3",
                        "title": "PyBench",
                        "app_version": "2018-02-16",
                        "description": "Total For Average Test Times",
                        "scale": "Milliseconds",
                        "proportion": "LIB",
                        "display_format": "BAR_GRAPH",
                        "results": {
                            "2025-12-12 22:22": {"value": 19504, "test_run_times": [500.33]}
                        },
                    }
                },
            },
            (
                "PTS test results\n\n"
                "System info:\n"
                "  Processor: Intel Xeon E3-12xx v2 (4 Cores)\n"
                "  Motherboard: QEMU Standard PC (Q35 + ICH9 2009) (rel-1.16.3-0-ga6ed6b701f0a-prebuilt.qemu.org BIOS)\n"
                "  Chipset: Intel 82G33/G31/P35/P31 + ICH9\n"
                "  Memory: 1 x 2 GB RAM QEMU\n"
                "  Disk: 10GB\n"
                "  OS: poky 5.2.4 (6.12.47-yocto-standard (x86_64))\n"
                "  File System: ext4\n"
                "  User: root\n\n"
                "Test results:\n\n"
                "  Test: PyBench\n"
                "    Description: Total For Average Test Times\n"
                "    Average response time / Performance: 19504 Milliseconds\n"
                "    Amount of iterations: 1\n"
                "      Iteration 1: 500.33 Seconds\n"
                "    Total time: 500.33 Seconds\n\n"
                "Summary:\n"
                "  Total tests: 1\n"
                "  Total iterations: 1\n"
                "  Total testing time: 500.33 Seconds\n"
                "    PyBench: 500.33 Seconds"
            ),
        ),
    ],
    ids=["pts empty results", "pts/pybench."],
)
def test_parse_metrics(raw_metrics: dict[str, Any], expected: str) -> None:
    pts = PhoronixTestSuite()
    result = pts.parse_metrics(raw_metrics)
    assert result == expected
