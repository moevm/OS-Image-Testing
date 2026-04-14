import json
import logging
import re
from typing import Any, Final, Literal, NamedTuple, get_args

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient, common_run_command
from imgtests.exec.osinfo import get_os_release
from imgtests.exec.pkgmgrs.zypper import Zypper
from imgtests.exec.utils import create_opt, extract_version
from imgtests.types import Distro, Version

logger = logging.getLogger(__name__)

_MAX_PERCENT: Final[int] = 100
_MAX_PORT: Final[int] = 65535
_MAX_OCTET_VALUE: Final[int] = 255

NetworkAction = Literal[
    "delay",
    "loss",
    "duplicate",
    "corrupt",
    "reorder",
    "drop",
    "dns",
    "dns_down",
    "occupy",
]
NetworkTraffic = Literal["in", "out"]
MemoryMode = Literal["ram", "cache"]
DiskAction = Literal["fill", "burn"]


class ChaosResponse(NamedTuple):
    code: int
    success: bool
    result: str | None = None
    error: str | None = None


class Chaosblade(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("blade", ssh_client)

    def install(self) -> ExecResult:
        """Install chaosblade from the official Git repository.

        Returns:
            ExecResult: Result of the installation.
        """
        if self.path:
            return ExecResult(
                cmd=(),
                stderr=f"{self.name} already has been installed.",
                returncode=0,
            )

        os_id = get_os_release(self.ssh_client).id
        if os_id and os_id == Distro.OPEN_SUSE_LEAP.value:
            zypper = Zypper(ssh_client=self.ssh_client, use_sudo=True)
            deps_result = zypper.install_packages(["wget", "tar"])
            if deps_result.returncode:
                return deps_result

        version = "1.8.0"
        arch = "linux_amd64"
        install_dir = "/opt/chaosblade"
        install_link = f"https://github.com/chaosblade-io/chaosblade/releases/download/v{version}/chaosblade-{version}-{arch}.tar.gz"

        script = (
            "set -e; "
            "tmpdir=$(mktemp -d); "
            "cd $tmpdir; "
            f"wget -q {install_link}; "
            f"tar -xzf chaosblade-{version}-{arch}.tar.gz; "
            f"mkdir -p {install_dir}; "
            f"cp -r chaosblade-{version}-{arch}/* {install_dir}/; "
            f"find {install_dir} -name '*.db' -o -name '*.sqlite*' -exec chmod 666 {{}} \\; ; "
            f"chown -R $(whoami) {install_dir}; "
            f"ln -sf {install_dir}/blade /usr/local/bin/blade; "
            f"chmod 755 {install_dir}/blade; "
            "cd /; "
            "rm -rf $tmpdir"
        )
        return common_run_command(("sudo", "bash", "-lc", f"'{script}'"), self.ssh_client)

    def version(self) -> Version | None:
        result = self(["version"])
        if result.returncode:
            return None
        return extract_version(result.stdout.strip())

    def check_env(self, experiment_type: str, action: str) -> tuple[ExecResult, ChaosResponse]:
        """Check if experiment supports specific experiment type and action.

        Args:
            experiment_type (str): Type of experiment (cpu, mem, network, disk).
            action (str): Specific action within experiment type.

        Returns:
            tuple[ExecResult, ChaosResponse]: Command execution result and parsed response.
        """
        result = self(["check", "os", experiment_type, action])
        return result, self._extract_result(result)

    def get_exp_status(self, experiment_id: str) -> tuple[ExecResult, ChaosResponse]:
        """Get status of an experiment by ID.

        Args:
            experiment_id (str): Identifier of the experiment.

        Returns:
            tuple[ExecResult, ChaosResponse]: Command execution result and parsed response.
        """
        result = self(["status", experiment_id])
        return result, self._extract_result(result)

    def destroy_exp(self, experiment_id: str) -> tuple[ExecResult, ChaosResponse]:
        """Destroy (stop) an experiment by ID.

        Args:
            experiment_id (str): Identifier of the experiment.

        Returns:
            tuple[ExecResult, ChaosResponse]: Command execution result and parsed response.
        """
        result = self(["destroy", experiment_id])
        return result, self._extract_result(result)

    def create_cpu_exp(
        self,
        cpu_percent: int | None = None,
        timeout_sec: int = 0,
        **kwargs: dict[str, Any],
    ) -> tuple[ExecResult, ChaosResponse]:
        """Create CPU load experiment.

        Args:
            cpu_percent (int | None): Percentage of CPU (0-100). If not specified occupy 100.
            timeout_sec (int): Experiment duration in seconds. When set to 0 run forever.
            **kwargs (dict[str, Any]): Command arguments in the free form with values.

        Raises:
            ValueError: When invalid parameters provided, required flags missing.

        Returns:
            tuple[ExecResult, ChaosResponse]: Command execution result and parsed response.
        """
        self._validate_cpu_params(cpu_percent, timeout_sec)

        result = self(
            [
                "create",
                "cpu",
                "fullload",
                *create_opt("timeout", timeout_sec),
                *create_opt("cpu-percent", cpu_percent),
            ],
            **kwargs,
        )
        return result, self._extract_result(result)

    def _validate_cpu_params(self, cpu_percent: int | None, timeout_sec: int) -> None:
        if cpu_percent is not None and not 0 <= cpu_percent <= _MAX_PERCENT:
            err_msg = f"Invalid cpu_percent '{cpu_percent}'. Expected 0-{_MAX_PERCENT}."
            raise ValueError(err_msg)
        if timeout_sec < 0:
            err_msg = f"Invalid timeout_sec '{timeout_sec}'. Expected more or equal 0."
            raise ValueError(err_msg)

    def create_memory_exp(  # noqa: PLR0913
        self,
        mem_percent: int | None = None,
        reserve_mb: int | None = None,
        timeout_sec: int | None = None,
        mode: MemoryMode = "ram",
        include_buffer_cache: bool = False,
        rate_mbps: int | None = None,
        **kwargs: dict[str, Any],
    ) -> tuple[ExecResult, ChaosResponse]:
        """Create memory load experiment.

        Args:
            mem_percent (int | None): Percentage of memory to occupy (0-100).
            reserve_mb (int | None): Free memory to keep free in MB.
            timeout_sec (int): Experiment duration in seconds. When set to 0 run forever.
            mode (MemoryMode): experiment mode (ram or cache).
            include_buffer_cache (bool): Include buffer, cache memory when calculating percentage.
            rate_mbps (int | None): Memory consupmtion rate in MB/s.
            **kwargs (dict[str, Any]): Command arguments in the free form with values.

        Raises:
            ValueError: When invalid parameters provided, required flags missing.

        Returns:
            tuple[ExecResult, ChaosResponse]: Command execution result and parsed response.
        """
        # Validation
        self._validate_memory_params(mem_percent, reserve_mb, timeout_sec, mode, rate_mbps)
        self._validate_memory_flags_compatibility(mode, rate_mbps, include_buffer_cache)

        # Build command
        ram_args: list[str] = []
        if mode == "ram":
            ram_args.extend(create_opt("include-buffer-cache", include_buffer_cache))
            ram_args.extend(create_opt("rate", rate_mbps))

        result = self(
            [
                "create",
                "mem",
                "load",
                *create_opt("mode", mode),
                *create_opt("timeout", timeout_sec),
                *create_opt("mem-percent", mem_percent),
                *create_opt("reserve", reserve_mb),
                *ram_args,
            ],
            **kwargs,
        )
        return result, self._extract_result(result)

    def _validate_memory_params(
        self,
        mem_percent: int | None,
        reserve_mb: int | None,
        timeout_sec: int | None,
        mode: MemoryMode,
        rate_mbps: int | None,
    ) -> None:
        if mem_percent is not None and not 0 <= mem_percent <= _MAX_PERCENT:
            err_msg = f"Invalid mem_percent '{mem_percent}'. Expected 0-{_MAX_PERCENT}."
            raise ValueError(err_msg)
        if reserve_mb is not None and reserve_mb < 0:
            err_msg = f"Invalid mem_reserve_mb '{reserve_mb}'. Expected more or equal 0."
            raise ValueError(err_msg)
        if timeout_sec is not None and timeout_sec < 0:
            err_msg = f"Invalid timeout_sec '{timeout_sec}'. Expected more or equal 0."
            raise ValueError(err_msg)
        if mode not in get_args(MemoryMode):
            err_msg = f"Invalid mem_mode '{mode}'. Expected one of {get_args(MemoryMode)}."
            raise ValueError(err_msg)
        if rate_mbps is not None and rate_mbps < 0:
            err_msg = f"Invalid mem_rate_mbps '{rate_mbps}'. Expected more or equal 0."
            raise ValueError(err_msg)

    def _validate_memory_flags_compatibility(
        self,
        mem_mode: MemoryMode,
        rate_mbps: int | None,
        include_buffer_cache: bool,
    ) -> None:
        if mem_mode == "cache" and rate_mbps is not None:
            err_msg = "--rate is only available in 'ram' mode"
            raise ValueError(err_msg)
        if mem_mode == "cache" and include_buffer_cache:
            err_msg = "--include_buffer_cache is only available in 'ram' mode"
            raise ValueError(err_msg)

    def create_disk_exp(  # noqa: PLR0913
        self,
        action: DiskAction,
        path: str = "/",
        timeout_sec: int | None = None,
        size_mb: int | None = None,
        percent: int | None = None,
        reserve_mb: int | None = None,
        read: bool = False,
        write: bool = False,
        retain_handle: bool = False,
        **kwargs: dict[str, Any],
    ) -> tuple[ExecResult, ChaosResponse]:
        """Create disk experiment.

        Args:
            action (DiskAction): experiment action (fill, burn).
            path (str): Target directory path. Default is '/'.
            timeout_sec (int): Experiment duration in seconds. When set to 0 run forever.
            size_mb (int | None): Data size in MB.
            percent (int | None): Percentage of disk space (0-100).
            reserve_mb (int | None): Disk space to leave free in MB.
            read (bool): Enable read I/O load.
            write (bool): Enable write I/O load.
            retain_handle (bool): Keep file handle open.
            **kwargs (dict[str, Any]): Command arguments in the free form with values.

        Raises:
            ValueError: When invalid parameters provided, required flags missing.

        Returns:
            tuple[ExecResult, ChaosResponse]: Command execution result and parsed response.
        """
        # Validation
        self._validate_disk_params(
            action,
            path,
            timeout_sec,
            percent,
            size_mb,
            reserve_mb,
            read,
            write,
        )

        # Build command
        action_args: list[str] = []
        if action == "fill":
            action_args.extend(create_opt("percent", percent))
            action_args.extend(create_opt("reserve", reserve_mb))
            action_args.extend(create_opt("retain-handle", retain_handle))
        elif action == "burn":
            action_args.extend(create_opt("read", read))
            action_args.extend(create_opt("write", write))
        result = self(
            [
                "create",
                "disk",
                action,
                *create_opt("path", path),
                *create_opt("size", size_mb),
                *create_opt("timeout", timeout_sec),
                *action_args,
            ],
            **kwargs,
        )
        return result, self._extract_result(result)

    def _validate_disk_params(  # noqa: PLR0913
        self,
        action: DiskAction,
        path: str,
        timeout_sec: int | None,
        percent: int | None,
        size_mb: int | None,
        reserve_mb: int | None,
        read: bool,
        write: bool,
    ) -> None:
        if action not in get_args(DiskAction):
            err_msg = f"Invalid action '{action}'. Expected one of {get_args(DiskAction)}."
            raise ValueError(err_msg)
        if not path:
            err_msg = "path cannot be empty."
            raise ValueError(err_msg)
        if timeout_sec is not None and timeout_sec < 0:
            err_msg = f"Invalid timeout_sec '{timeout_sec}'. Expected more or equal 0."
            raise ValueError(err_msg)
        if percent is not None and not 0 <= percent <= _MAX_PERCENT:
            err_msg = f"Invalid percent '{percent}'. Expected 0-{_MAX_PERCENT}."
            raise ValueError(err_msg)
        if size_mb is not None and size_mb < 0:
            err_msg = f"Invalid disk_size_mb '{size_mb}'. Expected more or equal 0."
            raise ValueError(err_msg)
        if reserve_mb is not None and reserve_mb < 0:
            err_msg = f"Invalid disk_reserve_mb '{reserve_mb}'. Expected more or equal 0."
            raise ValueError(err_msg)
        if action == "burn" and not (read or write):
            err_msg = "For burn, need read or write"
            raise ValueError(err_msg)
        if action == "burn" and not (size_mb or percent or reserve_mb):
            err_msg = "For burn, need one of size_mb or percent or reserve_mb"
            raise ValueError(err_msg)

    def create_network_exp(  # noqa: PLR0913
        self,
        action: NetworkAction,
        timeout_sec: int | None = None,
        interface: str | None = None,
        destination_ip: str | None = None,
        exclude_ip: str | None = None,
        percent: int | None = None,
        time_ms: int | None = None,
        offset_ms: int | None = None,
        correlation: int | None = None,
        gap: int | None = None,
        source_ip: str | None = None,
        source_port: int | None = None,
        destination_port: int | None = None,
        string_pattern: str | None = None,
        network_traffic: NetworkTraffic | None = None,
        domain: str | None = None,
        ip: str | None = None,
        allow_domain: str | None = None,
        force: bool = False,
        port: int | None = None,
        **kwargs: dict[str, Any],
    ) -> tuple[ExecResult, ChaosResponse]:
        """Create network experiment.

        Args:
            action (NetworkAction): experiment action (delay, loss, etc.).
            timeout_sec (int): Experiment duration in seconds. When set to 0 run forever.
            interface (str | None): Target network interface.
            destination_ip (str | None): Destination IP address.
            exclude_ip (str | None): IP to exclude from filtering.
            percent (int | None): Packet percentage (0-100).
            time_ms (int | None): Delay time in milliseconds.
            offset_ms (int | None): Delay offset/jitter in milliseconds.
            correlation (int | None): Correlation with previous packet (0-100).
            gap (int | None): Packet gap.
            source_ip (str | None): Source IP address of packet.
            source_port (int | None): Source port of packet.
            destination_port (int | None): Destination port of packet.
            string_pattern (str | None): String contained in packet payload.
            network_traffic (NetworkTraffic | None): Direction of traffic (in or out).
            domain (str | None): Domain name to manipulate.
            ip (str | None): IP address for DNS resolution.
            allow_domain (str | None): List of domains that should continue resolving.
            force (bool): Force kill process using the port.
            port (int | None): Port number.
            **kwargs (dict[str, Any]): Command arguments in the free form with values.

        Raises:
            ValueError: When invalid parameters provided, required flags missing.

        Returns:
            tuple[ExecResult, ChaosResponse]: Command execution result and parsed response.
        """
        # Validation
        self._validate_network_basic_params(
            action,
            timeout_sec,
            percent,
            time_ms,
            offset_ms,
            network_traffic,
            correlation,
            gap,
        )
        self._validate_network_ports(source_port, destination_port, port)
        self._validate_network_ips(source_ip, destination_ip, exclude_ip, ip)
        self._validate_network_flags_compatibility(
            action,
            percent,
            time_ms,
            domain,
            ip,
            port,
            source_ip,
            source_port,
            destination_port,
            interface,
        )

        # Build command
        action_args: list[str] = []
        if action in ["delay", "reorder"]:
            action_args.extend(create_opt("time", time_ms))
        if action == "delay":
            action_args.extend(create_opt("offset", offset_ms))
        if action in ["loss", "duplicate", "corrupt", "reorder"]:
            action_args.extend(create_opt("percent", percent))
        if action == "reorder":
            action_args.extend(create_opt("correlation", correlation))
            action_args.extend(create_opt("gap", gap))
        if action == "drop":
            action_args.extend(create_opt("source-ip", source_ip))
            action_args.extend(create_opt("source-port", source_port))
            action_args.extend(create_opt("destination-port", destination_port))
            action_args.extend(create_opt("string-pattern", string_pattern))
            action_args.extend(create_opt("network-traffic", network_traffic))
        if action == "dns":
            action_args.extend(create_opt("domain", domain))
            action_args.extend(create_opt("ip", ip))
        if action == "dns_down":
            action_args.extend(create_opt("allow-domain", allow_domain))
        if action == "occupy":
            action_args.extend(create_opt("force", force))
            action_args.extend(create_opt("port", port))
        if action in ["delay", "loss", "duplicate", "corrupt", "reorder"]:
            action_args.extend(create_opt("interface", interface))
            action_args.extend(create_opt("destination-ip", destination_ip))
            action_args.extend(create_opt("exclude-ip", exclude_ip))
        result = self(
            [
                "create",
                "network",
                action,
                *create_opt("timeout", timeout_sec),
                *action_args,
            ],
            **kwargs,
        )
        return result, self._extract_result(result)

    def _validate_network_basic_params(  # noqa: PLR0913
        self,
        action: NetworkAction,
        timeout_sec: int | None,
        percent: int | None,
        time_ms: int | None,
        offset_ms: int | None,
        network_traffic: NetworkTraffic | None,
        correlation: int | None = None,
        gap: int | None = None,
    ) -> None:
        if action not in get_args(NetworkAction):
            err_msg = f"Invalid action '{action}'. Expected one of {get_args(NetworkAction)}."
            raise ValueError(err_msg)

        if timeout_sec is not None and timeout_sec < 0:
            err_msg = f"Invalid timeout_sec '{timeout_sec}'. Expected more or equal 0."
            raise ValueError(err_msg)

        if percent is not None and not 0 <= percent <= _MAX_PERCENT:
            err_msg = f"Invalid percent '{percent}'. Expected 0-{_MAX_PERCENT}."
            raise ValueError(err_msg)

        if time_ms is not None and time_ms < 0:
            err_msg = f"Invalid time_ms '{time_ms}'. Expected more or equal 0."
            raise ValueError(err_msg)

        if offset_ms is not None and offset_ms < 0:
            err_msg = f"Invalid offset_ms '{offset_ms}'. Expected more or equal 0."
            raise ValueError(err_msg)

        if network_traffic is not None and network_traffic not in get_args(NetworkTraffic):
            err_msg = (
                f"Invalid network_traffic '{network_traffic}'. "
                f"Expected one of {get_args(NetworkTraffic)}."
            )
            raise ValueError(err_msg)

        if correlation is not None and not 0 <= correlation <= _MAX_PERCENT:
            err_msg = f"Invalid correlation '{correlation}'. Expected 0-{_MAX_PERCENT}."
            raise ValueError(err_msg)

        if gap is not None and gap <= 0:
            err_msg = f"Invalid gap '{gap}'. Expected more 0."
            raise ValueError(err_msg)

    def _validate_network_ports(
        self,
        source_port: int | None,
        destination_port: int | None,
        port: int | None,
    ) -> None:
        port_params = [
            (source_port, "source_port"),
            (destination_port, "destination_port"),
            (port, "port"),
        ]

        for param, param_name in port_params:
            if param is not None and not 0 <= param <= _MAX_PORT:
                err_msg = f"Invalid {param_name} '{param}'. Expected 0-{_MAX_PORT}."
                raise ValueError(err_msg)

    def _validate_network_ips(
        self,
        source_ip: str | None,
        destination_ip: str | None,
        exclude_ip: str | None,
        ip: str | None,
    ) -> None:
        ip_params = [
            (source_ip, "source_ip"),
            (destination_ip, "destination_ip"),
            (exclude_ip, "exclude_ip"),
            (ip, "ip"),
        ]

        for param, param_name in ip_params:
            if param is not None:
                pattern = r"^([0-9]{1,3}\.){3}[0-9]{1,3}$"
                if not re.match(pattern, param):
                    err_msg = f"{param_name} '{param}' must be valid IPv4"
                    raise ValueError(err_msg)

                parts = param.split(".")
                for i, part in enumerate(parts, 1):
                    if not part.isdigit():
                        err_msg = f"{param_name} octet {i} must be numeric"
                        raise ValueError(err_msg)

                    num = int(part)
                    if num < 0 or num > _MAX_OCTET_VALUE:
                        err_msg = f"{param_name} octet {i} must be 0-255"
                        raise ValueError(err_msg)

    def _validate_network_flags_compatibility(  # noqa: PLR0913
        self,
        action: NetworkAction,
        percent: int | None,
        time_ms: int | None,
        domain: str | None,
        ip: str | None,
        port: int | None,
        source_ip: str | None,
        source_port: int | None,
        destination_port: int | None,
        interface: str | None = None,
    ) -> None:
        if action in ["loss", "duplicate", "corrupt", "reorder"] and percent is None:
            err_msg = f"For {action}, percent is required"
            raise ValueError(err_msg)

        if action in ["delay", "reorder"] and time_ms is None:
            err_msg = f"For {action}, time_ms is required"
            raise ValueError(err_msg)

        if action == "dns":
            if domain is None:
                err_msg = "For dns, domain is required"
                raise ValueError(err_msg)
            if ip is None:
                err_msg = "For dns, ip is required"
                raise ValueError(err_msg)

        if action == "occupy" and port is None:
            err_msg = "For occupy, port is required"
            raise ValueError(err_msg)

        if action == "drop":
            params: list[str | None | int] = [source_ip, source_port, destination_port]
            if all(p is None for p in params):
                err_msg = "For drop, need at least one: source_ip, source_port, destination_port"
                raise ValueError(err_msg)

        if action in ["delay", "loss", "duplicate", "corrupt", "reorder"] and interface is None:
            err_msg = f"For {action}, interface is required"
            raise ValueError(err_msg)

    def _extract_result(self, result: ExecResult) -> ChaosResponse:
        if result.stderr:
            return Chaosblade.parse_result(result.stderr)
        return Chaosblade.parse_result(result.stdout)

    @staticmethod
    def parse_result(result: str) -> ChaosResponse:
        """Parse chaosblade output.

        Args:
            result (str): Raw chaosblade output.

        Returns:
            ChaosResponse: Parsed response.
        """
        if not result:
            return ChaosResponse(code=0, success=False, result=None, error="No output")

        try:
            data = json.loads(result.strip())
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse chaosblade result: '%s'. Error: %s", result, str(e))
            return ChaosResponse(
                code=500,
                success=False,
                result=None,
                error=f"Failed to parse: {result}",
            )
        return ChaosResponse(
            code=data.get("code", 0),
            success=data.get("success", False),
            result=data.get("result"),
            error=data.get("error"),
        )
