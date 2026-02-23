import logging
import re
from typing import TYPE_CHECKING, Any, Final, NamedTuple

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.utils import add_flag, create_opt

if TYPE_CHECKING:
    from imgtests.exec.exec import ExecResult, SSHClient

logger = logging.getLogger(__name__)


class StressNGVerifications(NamedTuple):
    always_enabled: tuple[str, ...]
    enabled_by_option: tuple[str, ...]
    not_implemented: tuple[str, ...]


class StressNGSyscallTiming(NamedTuple):
    name: str
    avg_ns: float
    min_ns: int
    max_ns: int


class StressNGMetrics(NamedTuple):
    stressor: str
    bogo_ops: int
    real_time_secs: float
    usr_time_secs: float
    sys_time_secs: float
    bogo_ops_s_real_time: float
    bogo_ops_s_usr_sys_time: float
    cpu_used_per_instance: float
    rss_max_kb: int | None = None
    top10_slowest: tuple[StressNGSyscallTiming, ...] | None = None


class StressNGSummary(NamedTuple):
    skipped: int
    passed: int
    failed: int
    metrics_untrustworthy: int


SYSCALL_ENTRY_RE: Final = re.compile(r"^syscall:\s+(\S+)\s+([\d.]+)\s+(\d+)\s+(\d+)$")
SPF_RE: Final = re.compile(r"^(skipped|passed|failed):\s*(\d+)(?::\s*([^\s()]+))?", re.IGNORECASE)
METRICS_UNTRUSTY_RE: Final = re.compile(r"metrics untrustworthy:\s*(\d+)", re.IGNORECASE)
CLEAN_LINE_RE: Final = re.compile(r"stress-ng: (?:info|metrc):\s+\[\d+\]\s*")
METRICS_RE: Final = re.compile(
    r"^(\S+)\s+"  # stressor name
    r"(\d+)\s+"  # bogo ops
    r"([\d.]+)\s+"  # real time
    r"([\d.]+)\s+"  # usr time
    r"([\d.]+)\s+"  # sys time
    r"([\d.]+)\s+"  # bogo ops/s (real time)
    r"([\d.]+)\s+"  # bogo ops/s (usr+sys time)
    r"([\d.]+)"  # CPU used per instance
    r"(?:\s+([\d]+))?$"  # RSS Max
)


class StressNg(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("stress-ng", ssh_client)

    def cpu_methods(self) -> tuple[str, ...] | None:
        result = self(["--cpu-method", "_which_"])
        # stress-ng exits with code 1 for this call
        if result.returncode != 1:
            return None
        return self.__parse_methods(result.stderr)

    def vm_methods(self) -> tuple[str, ...] | None:
        result = self(["--vm-method", "_which_"])
        # stress-ng exits with code 1 for this call
        if result.returncode != 1:
            return None
        return self.__parse_methods(result.stderr)

    def syscall_methods(self) -> tuple[str, ...] | None:
        result = self(["--syscall-method", "_which_"])
        # stress-ng exits with code 1 for this call
        if result.returncode != 1:
            return None
        return self.__parse_methods(result.stderr)

    def verifiable(self) -> StressNGVerifications | None:
        """Returns stressors that always enable verification or by option or not implements."""
        result = self(["--verifiable"])
        if result.returncode:
            return None
        always_enabled: tuple[str, ...] = ()
        enabled_by_option: tuple[str, ...] = ()
        not_implemented: tuple[str, ...] = ()
        for block in result.stdout.split("\n\n"):
            lines = block.strip().split("\n")
            header = lines[0].strip()
            items = " ".join(lines[1:]).strip().split()
            if header.startswith("Verification always enabled"):
                always_enabled = tuple(items)
            elif header.startswith("Verification enabled by --verify option"):
                enabled_by_option = tuple(items)
            elif header.startswith("Verification not implemented"):
                not_implemented = tuple(items)
        return StressNGVerifications(always_enabled, enabled_by_option, not_implemented)

    def run(  # noqa: PLR0913
        self,
        timeout_sec: int = 0,
        cpu: int | None = None,
        cpu_method: str = "all",
        vm: int | None = None,
        vm_method: str = "all",
        vm_bytes: str | None = None,
        hdd: int | None = None,
        hdd_bytes: str | None = None,
        hdd_opts: str | None = None,
        sock: int | None = None,
        sock_ops: int | None = None,
        netdev: int | None = None,
        udp_flood: int | None = None,
        iomix: int | None = None,
        iomix_bytes: str | None = None,
        syscall: int | None = None,
        syscall_method: str = "all",
        syscall_ops: str | None = None,
        mq: int | None = None,
        pipe: int | None = None,
        sem: int | None = None,
        shm: int | None = None,
        verify: bool = True,
        **kwargs: dict[str, Any],
    ) -> tuple[ExecResult, tuple[list[StressNGMetrics], StressNGSummary | None]]:
        """Runs the stress-ng util stressors.

        Args:
            timeout_sec (int): Execution time of stressors work. When set to 0 run 1 day
              stress test.
            cpu (int | None): Count of the CPU stressors. When set to 0 got count of logical
              processors.
            cpu_method (str): Stress CPU method.
            vm (int | None): Count of the virtual memory stressors. When set to 0 got count
              of logical processors.
            vm_method (str): Stress virtual memory method.
            vm_bytes (str | None): Utilized memory as value or percent of all available memory.
            hdd (int | None): Count of the HDD stressors. When set to 0 got count of logical
              processors.
            hdd_bytes (str | None): Utilized disk space as value or percent of all available disk.
            hdd_opts (str | None): Additional options for HDD stressor.
            sock (int | None): Count of the socket stressors. When set to 0 got count of logical
              processors.
            sock_ops (int | None): Number of socket operations per stressor.
            netdev (int | None): Count of the netdev stressors. When set to 0 got count of logical
              processors.
            udp_flood (int | None): Count of the udp stressors. When set to 0 got count of logical
              processors.
            iomix (int | None): Count of the I/O stressors. When set to 0 got count of logical
              processors.
            iomix_bytes (str | None): Utilized memory as value or percent of all available memory.
            syscall (int | None): Count of the syscall stressors. When set to 0 got count of logical
              processors.
            syscall_method (str): Stress syscall method.
            syscall_ops (str | None): Additional ops argument for syscall stressor.
            mq (int | None): Count of the message queue stressors. When set to 0 got count of
              logical processors.
            pipe (int | None): Count of the pipe stressors. When set to 0 got count of logical
              processors.
            sem (int | None): Count of the semaphore stressors. When set to 0 got count of logical
              processors.
            shm (int | None): Count of the shared memory stressors. When set to 0 got count of
              logical processors.
            verify (bool): Verify results if can.
            **kwargs (dict[str, Any]): Command arguments in the free form with values.

        Raises:
            ValueError: When invalid parameters provided or repeated.

        Returns:
            tuple[ExecResult, list[StressNGMetrics]]: Result of stress test work and parsed metrics.
        """
        params = {
            "cpu": cpu,
            "vm": vm,
            "hdd": hdd,
            "sock": sock,
            "netdev": netdev,
            "udp-flood": udp_flood,
            "iomix": iomix,
            "syscall": syscall,
            "mq": mq,
            "pipe": pipe,
            "sem": sem,
            "shm": shm,
        }
        if timeout_sec < 0:
            err_msg = f"Invalid timeout '{timeout_sec}'. Expected more or equal 0."
            raise ValueError(err_msg)

        for name, variable in params.items():
            if variable is not None and variable < 0:
                err_msg = f"Invalid {name} count '{variable}'. Expected more or equal 0."
                raise ValueError(err_msg)
        opts = [
            *create_opt("timeout", timeout_sec),
            *create_opt("cpu", cpu),
            *create_opt("cpu-method", cpu_method),
            *create_opt("vm", vm),
            *create_opt("vm-method", vm_method),
            *create_opt("vm-bytes", vm_bytes),
            *create_opt("hdd", hdd),
            *create_opt("hdd-bytes", hdd_bytes),
            *create_opt("hdd-opts", hdd_opts),
            *create_opt("sock", sock),
            *create_opt("sock-ops", sock_ops),
            *create_opt("netdev", netdev),
            *create_opt("udp-flood", udp_flood),
            *create_opt("iomix", iomix),
            *create_opt("iomix-bytes", iomix_bytes),
            *create_opt("syscall", syscall),
            *create_opt("syscall-method", syscall_method),
            *create_opt("syscall-ops", syscall_ops),
            *create_opt("mq", mq),
            *create_opt("pipe", pipe),
            *create_opt("sem", sem),
            *create_opt("shm", shm),
            *create_opt("verify", verify),
            *add_flag("metrics"),
        ]
        if syscall is not None:
            opts.extend(create_opt("syscall-top", 0))

        result = self(opts, **kwargs)

        if "stress-ng:" in result.stdout:
            return result, self.parse_metrics(result.stdout.strip())
        return result, self.parse_metrics(result.stderr.strip())

    @staticmethod
    def parse_metrics(  # noqa: PLR0915, PLR0912, C901
        raw_metrics: str,
    ) -> tuple[list[StressNGMetrics], StressNGSummary | None]:
        """Parse stress-ng metrics output.

        Args:
            raw_metrics (str): Raw stress-ng output metrics.
        """
        metrics_map: dict[str, dict[str, Any]] = {}

        summary_skipped: int | None = None
        summary_passed: int | None = None
        summary_failed: int | None = None
        summary_untrusty: int | None = None

        current_stressor: str | None = None
        for line in raw_metrics.splitlines():
            clean_line = CLEAN_LINE_RE.sub("", line).strip()
            if not clean_line:
                continue

            m = METRICS_RE.match(clean_line)
            if m is not None:
                try:
                    stressor_name = m.group(1)
                    bogo_ops_v = int(m.group(2))
                    real_time_v = float(m.group(3))
                    usr_time_v = float(m.group(4))
                    sys_time_v = float(m.group(5))
                    bogo_rt_v = float(m.group(6))
                    bogo_usrsys_v = float(m.group(7))
                    cpu_used_v = float(m.group(8))
                    rss_v = int(m.group(9)) if m.group(9) else None
                except ValueError as e:
                    logger.warning(
                        "Failed to parse stress-ng metrics line: '%s'. Error: %s",
                        clean_line,
                        str(e),
                    )
                    continue

                metrics_map.setdefault(
                    stressor_name,
                    {
                        "bogo_ops": 0,
                        "real_time_secs": 0.0,
                        "usr_time_secs": 0.0,
                        "sys_time_secs": 0.0,
                        "bogo_ops_s_real_time": 0.0,
                        "bogo_ops_s_usr_sys_time": 0.0,
                        "cpu_used_per_instance": 0.0,
                        "rss_max_kb": None,
                        "syscall_calls": [],
                    },
                )
                metrics_map[stressor_name].update(
                    {
                        "bogo_ops": bogo_ops_v,
                        "real_time_secs": real_time_v,
                        "usr_time_secs": usr_time_v,
                        "sys_time_secs": sys_time_v,
                        "bogo_ops_s_real_time": bogo_rt_v,
                        "bogo_ops_s_usr_sys_time": bogo_usrsys_v,
                        "cpu_used_per_instance": cpu_used_v,
                        "rss_max_kb": rss_v,
                    }
                )
                current_stressor = stressor_name
                continue

            m_syscall = SYSCALL_ENTRY_RE.match(clean_line)
            if m_syscall:
                name = m_syscall.group(1)
                try:
                    avg = float(m_syscall.group(2))
                    mn = int(m_syscall.group(3))
                    mx = int(m_syscall.group(4))
                except ValueError:
                    continue
                target = current_stressor or "syscall"
                metrics_map.setdefault(
                    target,
                    {
                        "bogo_ops": 0,
                        "real_time_secs": 0.0,
                        "usr_time_secs": 0.0,
                        "sys_time_secs": 0.0,
                        "bogo_ops_s_real_time": 0.0,
                        "bogo_ops_s_usr_sys_time": 0.0,
                        "cpu_used_per_instance": 0.0,
                        "rss_max_kb": None,
                        "syscall_calls": [],
                    },
                )
                metrics_map[target]["syscall_calls"].append(
                    StressNGSyscallTiming(name, avg, mn, mx)
                )
                current_stressor = target
                continue

            m_spf = SPF_RE.search(clean_line)
            if m_spf:
                key = m_spf.group(1).lower()
                try:
                    num = int(m_spf.group(2))
                except ValueError:
                    num = None

                if num is not None:
                    if key == "skipped":
                        summary_skipped = num
                    elif key == "passed":
                        summary_passed = num
                    elif key == "failed":
                        summary_failed = num
                continue

            m_untrusty = StressNg.__parse_untrusty(clean_line)
            if m_untrusty:
                summary_untrusty = m_untrusty

        metrics: list[StressNGMetrics] = []
        for stressor, info in metrics_map.items():
            raw_syscall_calls = info.get("syscall_calls") or None
            top10_slowest: tuple[StressNGSyscallTiming, ...] | None = None
            if raw_syscall_calls:
                items_sorted = sorted(raw_syscall_calls, key=lambda x: x.avg_ns, reverse=True)
                top10_slowest = tuple(items_sorted[:10])

            try:
                sm = StressNGMetrics(
                    stressor,
                    int(info.get("bogo_ops", 0)),
                    float(info.get("real_time_secs", 0.0)),
                    float(info.get("usr_time_secs", 0.0)),
                    float(info.get("sys_time_secs", 0.0)),
                    float(info.get("bogo_ops_s_real_time", 0.0)),
                    float(info.get("bogo_ops_s_usr_sys_time", 0.0)),
                    float(info.get("cpu_used_per_instance", 0.0)),
                    int(info.get("rss_max_kb")) if info.get("rss_max_kb") is not None else None,
                    top10_slowest,
                )
            except (ValueError, TypeError) as e:
                logger.warning(
                    "Failed to construct StressNGMetrics for '%s'. Error: %s", stressor, str(e)
                )
                continue
            metrics.append(sm)

        if not any([summary_skipped, summary_passed, summary_failed, summary_untrusty]):
            return metrics, None
        summary = StressNGSummary(
            skipped=summary_skipped or 0,
            passed=summary_passed or 0,
            failed=summary_failed or 0,
            metrics_untrustworthy=summary_untrusty or 0,
        )

        return metrics, summary

    @staticmethod
    def __parse_untrusty(line: str) -> int | None:
        m_untrusty = METRICS_UNTRUSTY_RE.search(line)
        if m_untrusty is None:
            return None
        try:
            num = int(m_untrusty.group(1))
        except ValueError:
            num = None
        return num

    def __parse_methods(self, raw_methods: str) -> tuple[str, ...] | None:
        try:
            methods = raw_methods.split(":", maxsplit=1)[1]
        except IndexError:
            return None
        return tuple(methods.strip().split())
