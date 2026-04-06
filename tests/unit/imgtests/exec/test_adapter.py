from typing import Any

import pytest

from imgtests.exec.adapter import IPerfAdapter, PerfAdapter, PTSAdapter, StressNgAdapter


@pytest.mark.parametrize(
    ("raw_metrics", "expected"),
    [
        (
            {
                "stress_ng_metrics": [
                    {
                        "stressor": "cpu",
                        "bogo_ops": 276,
                        "real_time_secs": 1.14,
                        "usr_time_secs": 4.14,
                        "sys_time_secs": 0.18,
                        "bogo_ops_s_real_time": 242.15,
                        "bogo_ops_s_usr_sys_time": 63.93,
                        "cpu_used_per_instance": 94.7,
                        "rss_max_kb": 6212,
                        "top10_slowest": None,
                    }
                ],
                "stress_ng_summary": {
                    "skipped": 0,
                    "passed": 4,
                    "failed": 0,
                    "metrics_untrustworthy": 0,
                },
            },
            {
                "tool": "stress-ng",
                "test_type": {
                    "stressor": "cpu",
                },
                "time": {
                    "real_time_secs": 1.14,
                    "usr_time_secs": 4.14,
                    "sys_time_secs": 0.18,
                },
                "metrics": {
                    "bogo_ops": 276,
                    "bogo_ops_s_real_time": 242.15,
                    "bogo_ops_s_usr_sys_time": 63.93,
                    "cpu_used_per_instance": 94.7,
                    "rss_max_kb": 6212,
                    "top10_slowest": None,
                },
                "summary": {
                    "skipped": 0,
                    "passed": 4,
                    "failed": 0,
                    "metrics_untrustworthy": 0,
                },
            },
        ),
    ],
    ids=[
        "Stress-ng adapter test.",
    ],
)
def test_stress_ng_parse_metrics(raw_metrics: dict[str, Any], expected: dict[str, Any]) -> None:
    adapter = StressNgAdapter()
    result = adapter(raw_metrics)
    assert result == expected


@pytest.mark.parametrize(
    ("raw_metrics", "expected"),
    [
        (
            [
                {
                    "benchmark": "sched/pipe",
                    "total_time": 198.97,
                    "usecs_per_op": 198.970091,
                    "ops_per_sec": 5025,
                }
            ],
            {
                "tool": "perf",
                "test_type": {
                    "benchmark": "sched/pipe",
                },
                "time": {
                    "total_time": 198.97,
                },
                "metrics": {
                    "usecs_per_op": 198.970091,
                    "ops_per_sec": 5025,
                },
                "summary": {},
            },
        ),
    ],
    ids=[
        "Perf adapter test.",
    ],
)
def test_perf_parse_metrics(raw_metrics: dict[str, Any], expected: dict[str, Any]) -> None:
    adapter = PerfAdapter()
    result = adapter(raw_metrics)
    assert result == expected


@pytest.mark.parametrize(
    ("raw_metrics", "expected"),
    [
        (
            {
                "client": {
                    "start": {
                        "connected": [
                            {
                                "socket": 5,
                                "local_host": "127.0.0.1",
                                "local_port": 45538,
                                "remote_host": "127.0.0.1",
                                "remote_port": 5201,
                            }
                        ],
                        "version": "iperf 3.18",
                        "system_info": "Linux qemux86-64 6.12.47-yocto-standard x86_64",
                        "timestamp": {
                            "time": "Sun, 05 Apr 2026 22:05:53 GMT",
                            "timesecs": 1775426753,
                        },
                        "connecting_to": {"host": "localhost", "port": 5201},
                        "cookie": "dyopoldniowo2jvialnl5lwejw6wjx3bln3b",
                        "target_bitrate": 1048576,
                        "fq_rate": 0,
                        "sock_bufsize": 0,
                        "sndbuf_actual": 212992,
                        "rcvbuf_actual": 212992,
                        "test_start": {
                            "protocol": "UDP",
                            "num_streams": 1,
                            "blksize": 32768,
                            "omit": 0,
                            "duration": 1,
                            "bytes": 0,
                            "blocks": 0,
                            "reverse": 0,
                            "tos": 0,
                            "target_bitrate": 1048576,
                            "bidir": 0,
                            "fqrate": 0,
                            "interval": 1,
                        },
                    },
                    "intervals": [
                        {
                            "streams": [
                                {
                                    "socket": 5,
                                    "start": 0,
                                    "end": 1.005694,
                                    "seconds": 1.005694031715393,
                                    "bytes": 163840,
                                    "bits_per_second": 1303298.9743056642,
                                    "packets": 5,
                                    "omitted": "false",
                                    "sender": "true",
                                }
                            ],
                            "sum": {
                                "start": 0,
                                "end": 1.005694,
                                "seconds": 1.005694031715393,
                                "bytes": 163840,
                                "bits_per_second": 1303298.9743056642,
                                "packets": 5,
                                "omitted": "false",
                                "sender": "true",
                            },
                        }
                    ],
                    "end": {
                        "streams": [
                            {
                                "udp": {
                                    "socket": 5,
                                    "start": 0,
                                    "end": 1.005694,
                                    "seconds": 1.005694,
                                    "bytes": 163840,
                                    "bits_per_second": 1303299.0154062766,
                                    "jitter_ms": 0.3490292816162109,
                                    "lost_packets": 0,
                                    "packets": 5,
                                    "lost_percent": 0,
                                    "out_of_order": 0,
                                    "sender": "true",
                                }
                            }
                        ],
                        "sum": {
                            "start": 0,
                            "end": 1.006723,
                            "seconds": 1.006723,
                            "bytes": 163840,
                            "bits_per_second": 1303299.0154062766,
                            "jitter_ms": 0.3490292816162109,
                            "lost_packets": 0,
                            "packets": 5,
                            "lost_percent": 0,
                            "sender": "true",
                        },
                        "sum_sent": {
                            "start": 0,
                            "end": 1.005694,
                            "seconds": 1.005694,
                            "bytes": 163840,
                            "bits_per_second": 1303299.0154062766,
                            "jitter_ms": 0,
                            "lost_packets": 0,
                            "packets": 5,
                            "lost_percent": 0,
                            "sender": "true",
                        },
                        "sum_received": {
                            "start": 0,
                            "end": 1.006723,
                            "seconds": 1.006723,
                            "bytes": 163840,
                            "bits_per_second": 1301966.8766880264,
                            "jitter_ms": 0.3490292816162109,
                            "lost_packets": 0,
                            "packets": 5,
                            "lost_percent": 0,
                            "sender": "false",
                        },
                        "cpu_utilization_percent": {
                            "host_total": 2.7494258492000685,
                            "host_user": 0.4593206399453781,
                            "host_system": 2.291366013376162,
                            "remote_total": 1.8860973187686196,
                            "remote_user": 0.772591857000993,
                            "remote_system": 1.1143992055610725,
                        },
                    },
                },
                "server": {
                    "start": {
                        "connected": [
                            {
                                "socket": 5,
                                "local_host": "127.0.0.1",
                                "local_port": 5201,
                                "remote_host": "127.0.0.1",
                                "remote_port": 45538,
                            }
                        ],
                        "version": "iperf 3.18",
                        "system_info": "Linux qemux86-64 6.12.47-yocto-standard x86_64",
                        "target_bitrate": 1048576,
                        "timestamp": {
                            "time": "Sun, 05 Apr 2026 22:05:53 GMT",
                            "timesecs": 1775426753,
                        },
                        "accepted_connection": {"host": "127.0.0.1", "port": 33678},
                        "cookie": "dyopoldniowo2jvialnl5lwejw6wjx3bln3b",
                        "fq_rate": 0,
                        "sock_bufsize": 0,
                        "sndbuf_actual": 212992,
                        "rcvbuf_actual": 212992,
                        "test_start": {
                            "protocol": "UDP",
                            "num_streams": 1,
                            "blksize": 32768,
                            "omit": 0,
                            "duration": 1,
                            "bytes": 0,
                            "blocks": 0,
                            "reverse": 0,
                            "tos": 0,
                            "target_bitrate": 1048576,
                            "bidir": 0,
                            "fqrate": 0,
                            "interval": 1,
                        },
                    },
                    "intervals": [
                        {
                            "streams": [
                                {
                                    "socket": 5,
                                    "start": 0,
                                    "end": 1.000781,
                                    "seconds": 1.0007810592651367,
                                    "bytes": 131072,
                                    "bits_per_second": 1047757.6391882942,
                                    "jitter_ms": 0.327097900390625,
                                    "lost_packets": 0,
                                    "packets": 4,
                                    "lost_percent": 0,
                                    "omitted": "false",
                                    "sender": "false",
                                }
                            ],
                            "sum": {
                                "start": 0,
                                "end": 1.000781,
                                "seconds": 1.0007810592651367,
                                "bytes": 131072,
                                "bits_per_second": 1047757.6391882942,
                                "jitter_ms": 0.327097900390625,
                                "lost_packets": 0,
                                "packets": 4,
                                "lost_percent": 0,
                                "omitted": "false",
                                "sender": "false",
                            },
                        },
                        {
                            "streams": [
                                {
                                    "socket": 5,
                                    "start": 1.000781,
                                    "end": 1.006723,
                                    "seconds": 0.005942000076174736,
                                    "bytes": 32768,
                                    "bits_per_second": 44117131.713125065,
                                    "jitter_ms": 0.3490292816162109,
                                    "lost_packets": 0,
                                    "packets": 1,
                                    "lost_percent": 0,
                                    "omitted": "false",
                                    "sender": "false",
                                }
                            ],
                            "sum": {
                                "start": 1.000781,
                                "end": 1.006723,
                                "seconds": 0.005942000076174736,
                                "bytes": 32768,
                                "bits_per_second": 44117131.713125065,
                                "jitter_ms": 0.3490292816162109,
                                "lost_packets": 0,
                                "packets": 1,
                                "lost_percent": 0,
                                "omitted": "false",
                                "sender": "false",
                            },
                        },
                    ],
                    "end": {
                        "streams": [
                            {
                                "udp": {
                                    "socket": 5,
                                    "start": 0,
                                    "end": 1.006723,
                                    "seconds": 1.006723,
                                    "bytes": 0,
                                    "bits_per_second": 0,
                                    "jitter_ms": 0.3490292816162109,
                                    "lost_packets": 0,
                                    "packets": 5,
                                    "lost_percent": 0,
                                    "out_of_order": 0,
                                    "sender": "false",
                                }
                            }
                        ],
                        "sum": {
                            "start": 0,
                            "end": 1.006723,
                            "seconds": 1.006723,
                            "bytes": 0,
                            "bits_per_second": 0,
                            "jitter_ms": 0.3490292816162109,
                            "lost_packets": 0,
                            "packets": 5,
                            "lost_percent": 0,
                            "sender": "false",
                        },
                        "sum_sent": {
                            "start": 0,
                            "end": 1.006723,
                            "seconds": 1.006723,
                            "bytes": 0,
                            "bits_per_second": 0,
                            "jitter_ms": 0,
                            "lost_packets": 0,
                            "packets": 0,
                            "lost_percent": 0,
                            "sender": "true",
                        },
                        "sum_received": {
                            "start": 0,
                            "end": 1.006723,
                            "seconds": 1.006723,
                            "bytes": 163840,
                            "bits_per_second": 1301966.8766880264,
                            "jitter_ms": 0.3490292816162109,
                            "lost_packets": 0,
                            "packets": 5,
                            "lost_percent": 0,
                            "sender": "false",
                        },
                        "cpu_utilization_percent": {
                            "host_total": 1.8860973187686196,
                            "host_user": 0.772591857000993,
                            "host_system": 1.1143992055610725,
                            "remote_total": 0,
                            "remote_user": 0,
                            "remote_system": 0,
                        },
                    },
                },
            },
            {
                "tool": "iperf3",
                "test_type": {
                    "protocol": "UDP",
                },
                "time": {
                    "duration_sec": 1.0,
                },
                "metrics": {
                    "client": {
                        "sum_sent": {
                            "start": 0,
                            "end": 1.005694,
                            "seconds": 1.005694,
                            "bytes": 163840,
                            "bits_per_second": 1303299.0154062766,
                            "jitter_ms": 0,
                            "lost_packets": 0,
                            "packets": 5,
                            "lost_percent": 0,
                            "sender": "true",
                        },
                        "sum_received": {
                            "start": 0,
                            "end": 1.006723,
                            "seconds": 1.006723,
                            "bytes": 163840,
                            "bits_per_second": 1301966.8766880264,
                            "jitter_ms": 0.3490292816162109,
                            "lost_packets": 0,
                            "packets": 5,
                            "lost_percent": 0,
                            "sender": "false",
                        },
                        "cpu_utilization_percent": {
                            "host_total": 2.7494258492000685,
                            "host_user": 0.4593206399453781,
                            "host_system": 2.291366013376162,
                            "remote_total": 1.8860973187686196,
                            "remote_user": 0.772591857000993,
                            "remote_system": 1.1143992055610725,
                        },
                    },
                    "server": {
                        "sum_sent": {
                            "start": 0,
                            "end": 1.006723,
                            "seconds": 1.006723,
                            "bytes": 0,
                            "bits_per_second": 0,
                            "jitter_ms": 0,
                            "lost_packets": 0,
                            "packets": 0,
                            "lost_percent": 0,
                            "sender": "true",
                        },
                        "sum_received": {
                            "start": 0,
                            "end": 1.006723,
                            "seconds": 1.006723,
                            "bytes": 163840,
                            "bits_per_second": 1301966.8766880264,
                            "jitter_ms": 0.3490292816162109,
                            "lost_packets": 0,
                            "packets": 5,
                            "lost_percent": 0,
                            "sender": "false",
                        },
                        "cpu_utilization_percent": {
                            "host_total": 1.8860973187686196,
                            "host_user": 0.772591857000993,
                            "host_system": 1.1143992055610725,
                            "remote_total": 0,
                            "remote_user": 0,
                            "remote_system": 0,
                        },
                    },
                },
                "summary": {},
            },
        ),
    ],
    ids=[
        "Iperf3 adapter test.",
    ],
)
def test_iperf3_parse_metrics(raw_metrics: dict[str, Any], expected: dict[str, Any]) -> None:
    adapter = IPerfAdapter()
    result = adapter(raw_metrics)
    assert result == expected


@pytest.mark.parametrize(
    ("raw_metrics", "expected"),
    [
        (
            {
                "title": "2026-04-05-2206",
                "last_modified": "2026-04-05 22:12:17",
                "description": "qemu testing on poky 5.2.4 via the Phoronix Test Suite.",
                "systems": {
                    "2026-04-05 22:06": {
                        "identifier": "2026-04-05 22:06",
                        "hardware": {
                            "Processor": "Intel Xeon E3-12xx v2 (4 Cores)",
                            "Motherboard": "QEMU Standard PC (Q35 + ICH9 2009)",
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
                            "System Layer": "qemu",
                        },
                        "user": "root",
                        "timestamp": "2026-04-05 22:07:04",
                        "client_version": "10.8.4",
                        "data": {
                            "compiler-configuration": "",
                            "cpu-microcode": "0x1",
                            "security": "",
                        },
                    }
                },
                "results": {
                    "d14fab923a8a05c721a245a14d1b704edb4f77f8": {
                        "identifier": "pts/ctx-clock-1.0.0",
                        "title": "ctx_clock",
                        "description": "Context Switch Time",
                        "scale": "Clocks",
                        "proportion": "LIB",
                        "display_format": "BAR_GRAPH",
                        "results": {
                            "2026-04-05 22:06": {
                                "value": 19585,
                                "raw_values": [
                                    19573,
                                    19596,
                                ],
                                "test_run_times": [
                                    154.03,
                                    150.62,
                                ],
                                "details": {
                                    "compiler-options": {
                                        "compiler-type": "CC",
                                        "compiler": "gcc",
                                        "compiler-options": "",
                                    }
                                },
                            }
                        },
                    }
                },
            },
            {
                "tool": "pts",
                "test_type": {
                    "identifier": "pts/ctx-clock-1.0.0",
                    "title": "ctx_clock",
                    "description": "Context Switch Time",
                },
                "time": {
                    "timestamp": "2026-04-05 22:07:04",
                },
                "metrics": {
                    "value": 19585,
                    "raw_values": [
                        19573,
                        19596,
                    ],
                    "test_run_times": [
                        154.03,
                        150.62,
                    ],
                },
                "summary": {},
            },
        ),
    ],
    ids=[
        "PTS adapter test.",
    ],
)
def test_pts_parse_metrics(raw_metrics: dict[str, Any], expected: dict[str, Any]) -> None:
    adapter = PTSAdapter()
    result = adapter(raw_metrics)
    assert result == expected
