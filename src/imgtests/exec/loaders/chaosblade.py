import json
import logging
import re
from typing import Any, NamedTuple

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient
from imgtests.exec.utils import create_opt

logger = logging.getLogger(__name__)

SUCCESS_CODE = 200
MAX_PERCENT = 100
MAX_PORT = 65535
MAX_OCTET_VALUE = 255


class ChaosResponse(NamedTuple):
    code: int
    success: bool
    result: str | None = None
    error: str | None = None


class Chaosblade(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("blade", ssh_client)

    def check_env(self, experiment_type: str, action: str) -> ChaosResponse:
        result = self(["check", "os", experiment_type, action])
        return self._parse_result(result)

    def get_exp_status(self, experiment_id: str) -> ChaosResponse:
        result = self(["status", experiment_id])
        return self._parse_result(result)

    def destroy_exp(self, experiment_id: str) -> ChaosResponse:
        result = self(["destroy", experiment_id])
        return self._parse_result(result)

    def create_cpu_exp(
        self, cpu_percent: int | None = None, timeout_sec: int = 0, **kwargs: dict[str, Any]
    ) -> ChaosResponse:
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
        return self._parse_result(result)

    def _validate_cpu_params(self, cpu_percent: int | None, timeout_sec: int) -> None:
        if cpu_percent is not None and not 0 < cpu_percent < MAX_PERCENT:
            err_msg = f"Invalid cpu_percent '{cpu_percent}'. Expected 0-100."
            raise ValueError(err_msg)
        if timeout_sec < 0:
            err_msg = f"Invalid timeout_sec '{timeout_sec}'. Expected more or equal 0."
            raise ValueError(err_msg)

    def create_memory_exp(  # noqa: PLR0913
        self,
        mem_percent: int | None = None,
        mem_reserve_mb: int | None = None,
        timeout_sec: int | None = None,
        mem_mode: str = "ram",
        mem_include_buffer_cache: bool = False,
        mem_rate_mbps: int | None = None,
        **kwargs: dict[str, Any],
    ) -> ChaosResponse:
        # Validation
        self._validate_memory_params(
            mem_percent, mem_reserve_mb, timeout_sec, mem_mode, mem_rate_mbps
        )
        self._validate_memory_flags_compatibility(mem_mode, mem_rate_mbps, mem_include_buffer_cache)

        # Build command
        ram_args = []
        if mem_mode == "ram":
            ram_args.extend(create_opt("include-buffer-cache", mem_include_buffer_cache))
            ram_args.extend(create_opt("rate", mem_rate_mbps))

        result = self(
            [
                "create",
                "mem",
                "load",
                *create_opt("mode", mem_mode),
                *create_opt("timeout", timeout_sec),
                *create_opt("mem-percent", mem_percent),
                *create_opt("reserve", mem_reserve_mb),
                *ram_args,
            ],
            **kwargs,
        )
        return self._parse_result(result)

    def _validate_memory_params(
        self,
        mem_percent: int | None,
        mem_reserve_mb: int | None,
        timeout_sec: int | None,
        mem_mode: str,
        mem_rate_mbps: int | None,
    ) -> None:
        if mem_percent is not None and not 0 < mem_percent < MAX_PERCENT:
            err_msg = f"Invalid mem_percent '{mem_percent}'. Expected 0-100."
            raise ValueError(err_msg)
        if mem_reserve_mb is not None and mem_reserve_mb < 0:
            err_msg = f"Invalid mem_reserve_mb '{mem_reserve_mb}'. Expected more or equal 0."
            raise ValueError(err_msg)
        if timeout_sec is not None and timeout_sec < 0:
            err_msg = f"Invalid timeout_sec '{timeout_sec}'. Expected more or equal 0."
            raise ValueError(err_msg)
        if mem_mode not in ["ram", "cache"]:
            err_msg = f"Invalid mem_mode '{mem_mode}'. Expected 'ram' or 'cache'."
            raise ValueError(err_msg)
        if mem_rate_mbps is not None and mem_rate_mbps < 0:
            err_msg = f"Invalid mem_rate_mbps '{mem_rate_mbps}'. Expected more or equal 0."
            raise ValueError(err_msg)

    def _validate_memory_flags_compatibility(
        self, mem_mode: str, mem_rate_mbps: int | None, mem_include_buffer_cache: bool
    ) -> None:
        if mem_mode == "cache" and mem_rate_mbps is not None:
            err_msg = "--rate is only available in 'ram' mode"
            raise ValueError(err_msg)
        if mem_mode == "cache" and mem_include_buffer_cache:
            err_msg = "include_buffer_cache is only available in 'ram' mode"
            raise ValueError(err_msg)

    def create_disk_exp(  # noqa: PLR0913
        self,
        disk_action: str,
        disk_path: str = "/",
        timeout_sec: int | None = None,
        disk_size_mb: int | None = None,
        disk_percent: int | None = None,
        disk_reserve_mb: int | None = None,
        disk_read: bool = False,
        disk_write: bool = False,
        disk_retain_handle: bool = False,
        **kwargs: dict[str, Any],
    ) -> ChaosResponse:
        # Validation
        self._validate_disk_params(
            disk_action,
            disk_path,
            timeout_sec,
            disk_percent,
            disk_size_mb,
            disk_reserve_mb,
            disk_read,
            disk_write,
        )

        action_args = []
        if disk_action == "fill":
            action_args.extend(create_opt("percent", disk_percent))
            action_args.extend(create_opt("reserve", disk_reserve_mb))
            action_args.extend(create_opt("retain-handle", disk_retain_handle))
        elif disk_action == "burn":
            action_args.extend(create_opt("read", disk_read))
            action_args.extend(create_opt("write", disk_write))
        result = self(
            [
                "create",
                "disk",
                disk_action,
                *create_opt("path", disk_path),
                *create_opt("size", disk_size_mb),
                *create_opt("timeout", timeout_sec),
            ],
            **kwargs,
        )
        return self._parse_result(result)

    def _validate_disk_params(  # noqa: PLR0913
        self,
        disk_action: str,
        disk_path: str,
        timeout_sec: int | None,
        disk_percent: int | None,
        disk_size_mb: int | None,
        disk_reserve_mb: int | None,
        disk_read: bool,
        disk_write: bool,
    ) -> None:
        if disk_action not in ["fill", "burn"]:
            err_msg = f"Invalid disk_action '{disk_action}'. Expected 'fill' or 'burn'."
            raise ValueError(err_msg)
        if not disk_path:
            err_msg = "disk_path cannot be empty."
            raise ValueError(err_msg)
        if timeout_sec is not None and timeout_sec < 0:
            err_msg = f"Invalid timeout_sec '{timeout_sec}'. Expected more or equal 0."
            raise ValueError(err_msg)
        if disk_percent is not None and not 0 < disk_percent < MAX_PERCENT:
            err_msg = f"Invalid disk_percent '{disk_percent}'. Expected 0-100."
            raise ValueError(err_msg)
        if disk_size_mb is not None and disk_size_mb < 0:
            err_msg = f"Invalid disk_size_mb '{disk_size_mb}'. Expected more or equal 0."
            raise ValueError(err_msg)
        if disk_reserve_mb is not None and disk_reserve_mb < 0:
            err_msg = f"Invalid disk_reserve_mb '{disk_reserve_mb}'. Expected more or equal 0."
            raise ValueError(err_msg)
        if disk_action == "burn" and not (disk_read or disk_write):
            err_msg = "For burn, need disk_read or disk_write"
            raise ValueError(err_msg)

    def create_network_exp(  # noqa: PLR0913
        self,
        network_action: str,
        timeout_sec: int | None = None,
        network_interface: str | None = None,
        network_destination_ip: str | None = None,
        network_exclude_ip: str | None = None,
        network_percent: int | None = None,
        network_time_ms: int | None = None,
        network_offset_ms: int | None = None,
        network_correlation: int | None = None,
        network_gap: int | None = None,
        network_source_ip: str | None = None,
        network_source_port: int | None = None,
        network_destination_port: int | None = None,
        network_string_pattern: str | None = None,
        network_traffic: str | None = None,
        network_domain: str | None = None,
        network_ip: str | None = None,
        network_allow_domain: str | None = None,
        network_force: bool = False,
        network_port: int | None = None,
        **kwargs: dict[str, Any],
    ) -> ChaosResponse:
        # Validation
        self._validate_network_basic_params(
            network_action,
            timeout_sec,
            network_percent,
            network_time_ms,
            network_offset_ms,
            network_traffic,
        )
        self._validate_network_ports(network_source_port, network_destination_port, network_port)
        self._validate_network_action_specific(
            network_action,
            network_percent,
            network_time_ms,
            network_domain,
            network_ip,
            network_port,
            network_source_ip,
            network_source_port,
            network_destination_port,
        )
        self._validate_network_ips(
            network_source_ip, network_destination_ip, network_exclude_ip, network_ip
        )

        # Build command
        args = self._build_network_args(
            network_action,
            timeout_sec,
            network_interface,
            network_destination_ip,
            network_exclude_ip,
            network_percent,
            network_time_ms,
            network_offset_ms,
            network_correlation,
            network_gap,
            network_source_ip,
            network_source_port,
            network_destination_port,
            network_string_pattern,
            network_traffic,
            network_domain,
            network_ip,
            network_allow_domain,
            network_force,
            network_port,
        )

        result = self(args, **kwargs)
        return self._parse_result(result)

    def _validate_ip(self, ip: str, param_name: str) -> None:
        pattern = r"^([0-9]{1,3}\.){3}[0-9]{1,3}$"
        if not re.match(pattern, ip):
            err_msg = f"{param_name} '{ip}' must be valid IPv4"
            raise ValueError(err_msg)

        parts = ip.split(".")

        for i, part in enumerate(parts, 1):
            if not part.isdigit():
                err_msg = f"{param_name} octet {i} must be numeric"
                raise ValueError(err_msg)

            num = int(part)
            if num < 0 or num > MAX_OCTET_VALUE:
                err_msg = f"{param_name} octet {i} must be 0-255"
                raise ValueError(err_msg)

    def _validate_network_basic_params(  # noqa: PLR0913
        self,
        network_action: str,
        timeout_sec: int | None,
        network_percent: int | None,
        network_time_ms: int | None,
        network_offset_ms: int | None,
        network_traffic: str | None,
    ) -> None:
        valid_actions = [
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

        if network_action not in valid_actions:
            err_msg = f"Invalid network_action '{network_action}'. Expected one of {valid_actions}."
            raise ValueError(err_msg)

        if timeout_sec is not None and timeout_sec < 0:
            err_msg = f"Invalid timeout_sec '{timeout_sec}'. Expected more or equal 0."
            raise ValueError(err_msg)

        if network_percent is not None and not 0 < network_percent < MAX_PERCENT:
            err_msg = f"Invalid network_percent '{network_percent}'. Expected 0-100."
            raise ValueError(err_msg)

        if network_time_ms is not None and network_time_ms < 0:
            err_msg = f"Invalid network_time_ms '{network_time_ms}'. Expected more or equal 0."
            raise ValueError(err_msg)

        if network_offset_ms is not None and network_offset_ms < 0:
            err_msg = f"Invalid network_offset_ms '{network_offset_ms}'. Expected more or equal 0."
            raise ValueError(err_msg)

        if network_traffic is not None and network_traffic not in ["in", "out"]:
            err_msg = f"Invalid network_traffic '{network_traffic}'. Expected 'in' or 'out'."
            raise ValueError(err_msg)

    def _validate_network_ports(
        self,
        network_source_port: int | None,
        network_destination_port: int | None,
        network_port: int | None,
    ) -> None:
        port_params = [
            (network_source_port, "network_source_port"),
            (network_destination_port, "network_destination_port"),
            (network_port, "network_port"),
        ]

        for port, param_name in port_params:
            if port is not None and not 0 <= port <= MAX_PORT:
                err_msg = f"Invalid {param_name} '{port}'. Expected 0-65535."
                raise ValueError(err_msg)

    def _validate_network_action_specific(  # noqa: PLR0913
        self,
        network_action: str,
        network_percent: int | None,
        network_time_ms: int | None,
        network_domain: str | None,
        network_ip: str | None,
        network_port: int | None,
        network_source_ip: str | None,
        network_source_port: int | None,
        network_destination_port: int | None,
    ) -> None:
        if (
            network_action in ["loss", "duplicate", "corrupt", "reorder"]
            and network_percent is None
        ):
            err_msg = f"For {network_action}, network_percent is required"
            raise ValueError(err_msg)

        if network_action in ["delay", "reorder"] and network_time_ms is None:
            err_msg = f"For {network_action}, network_time_ms is required"
            raise ValueError(err_msg)

        if network_action == "dns":
            if network_domain is None:
                err_msg = "For dns, network_domain is required"
                raise ValueError(err_msg)
            if network_ip is None:
                err_msg = "For dns, network_ip is required"
                raise ValueError(err_msg)

        if network_action == "occupy" and network_port is None:
            err_msg = "For occupy, network_port is required"
            raise ValueError(err_msg)

        if network_action == "drop":
            params = [network_source_ip, network_source_port, network_destination_port]
            if all(p is None for p in params):
                err_msg = "For drop, need at least one: source_ip, source_port, or destination_port"
                raise ValueError(err_msg)

    def _validate_network_ips(
        self,
        network_source_ip: str | None,
        network_destination_ip: str | None,
        network_exclude_ip: str | None,
        network_ip: str | None,
    ) -> None:
        if network_source_ip is not None:
            self._validate_ip(network_source_ip, "network_source_ip")
        if network_destination_ip is not None:
            self._validate_ip(network_destination_ip, "network_destination_ip")
        if network_exclude_ip is not None:
            self._validate_ip(network_exclude_ip, "network_exclude_ip")
        if network_ip is not None:
            self._validate_ip(network_ip, "network_ip")

    def _build_network_args(  # noqa: PLR0913
        self,
        network_action: str,
        timeout_sec: int | None,
        network_interface: str | None,
        network_destination_ip: str | None,
        network_exclude_ip: str | None,
        network_percent: int | None,
        network_time_ms: int | None,
        network_offset_ms: int | None,
        network_correlation: int | None,
        network_gap: int | None,
        network_source_ip: str | None,
        network_source_port: int | None,
        network_destination_port: int | None,
        network_string_pattern: str | None,
        network_traffic: str | None,
        network_domain: str | None,
        network_ip: str | None,
        network_allow_domain: str | None,
        network_force: bool,
        network_port: int | None,
    ) -> list[str]:
        args = ["create", "network", network_action]

        args = self._add_network_common_args(
            args, network_interface, network_destination_ip, network_exclude_ip, timeout_sec
        )

        return self._add_network_action_specific_args(
            args,
            network_action,
            network_percent,
            network_time_ms,
            network_offset_ms,
            network_correlation,
            network_gap,
            network_source_ip,
            network_source_port,
            network_destination_port,
            network_string_pattern,
            network_traffic,
            network_domain,
            network_ip,
            network_allow_domain,
            network_force,
            network_port,
        )

    def _add_network_common_args(
        self,
        args: list[str],
        network_interface: str | None,
        network_destination_ip: str | None,
        network_exclude_ip: str | None,
        timeout_sec: int | None,
    ) -> list[str]:
        if network_interface is not None:
            args.extend(["--interface", network_interface])
        if network_destination_ip is not None:
            args.extend(["--destination-ip", network_destination_ip])
        if network_exclude_ip is not None:
            args.extend(["--exclude-ip", network_exclude_ip])
        if timeout_sec is not None:
            args.extend(["--timeout", str(timeout_sec)])

        return args

    def _add_network_action_specific_args(  # noqa: PLR0913 PLR0912 C901
        self,
        args: list[str],
        network_action: str,
        network_percent: int | None,
        network_time_ms: int | None,
        network_offset_ms: int | None,
        network_correlation: int | None,
        network_gap: int | None,
        network_source_ip: str | None,
        network_source_port: int | None,
        network_destination_port: int | None,
        network_string_pattern: str | None,
        network_traffic: str | None,
        network_domain: str | None,
        network_ip: str | None,
        network_allow_domain: str | None,
        network_force: bool,
        network_port: int | None,
    ) -> list[str]:
        if network_action in ["delay", "reorder"] and network_time_ms is not None:
            args.extend(["--time", str(network_time_ms)])

        if network_action == "delay" and network_offset_ms is not None:
            args.extend(["--offset", str(network_offset_ms)])

        if (
            network_action in ["loss", "duplicate", "corrupt", "reorder"]
            and network_percent is not None
        ):
            args.extend(["--percent", str(network_percent)])

        if network_action == "reorder":
            if network_correlation is not None:
                args.extend(["--correlation", str(network_correlation)])
            if network_gap is not None:
                args.extend(["--gap", str(network_gap)])

        if network_action == "drop":
            if network_source_ip is not None:
                args.extend(["--source-ip", network_source_ip])
            if network_source_port is not None:
                args.extend(["--source-port", str(network_source_port)])
            if network_destination_port is not None:
                args.extend(["--destination-port", str(network_destination_port)])
            if network_string_pattern is not None:
                args.extend(["--string-pattern", network_string_pattern])
            if network_traffic is not None:
                args.extend(["--network-traffic", network_traffic])

        if network_action == "dns":
            if network_domain is not None:
                args.extend(["--domain", network_domain])
            if network_ip is not None:
                args.extend(["--ip", network_ip])

        if network_action == "dns_down" and network_allow_domain is not None:
            args.extend(["--allow-domain", network_allow_domain])

        if network_action == "occupy":
            if network_force:
                args.append("--force")
            if network_port is not None:
                args.extend(["--port", str(network_port)])

        return args

    def _parse_result(self, result: ExecResult) -> ChaosResponse:
        if not result.stdout:
            return ChaosResponse(
                code=500, success=False, result=None, error=result.stderr or "No output"
            )

        try:
            data = json.loads(result.stdout)
            return ChaosResponse(
                code=data.get("code", 0),
                success=data.get("success", False),
                result=data.get("result"),
                error=data.get("error"),
            )
        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to parse chaosblade result: '%s'. Error: %s", result.stdout, str(e)
            )
            return ChaosResponse(
                code=500, success=False, result=None, error=f"Failed to parse: {result.stdout}"
            )
