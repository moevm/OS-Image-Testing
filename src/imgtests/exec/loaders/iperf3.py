import json
from typing import TYPE_CHECKING, Any

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult
from imgtests.exec.pkgmgrs.mixin import PkgMgrMixin
from imgtests.exec.utils import add_flag, create_opt

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient


class Iperf3(PkgMgrMixin, GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("iperf3", ssh_client)

    def run(  # noqa: PLR0913
        self,
        port: int = 5201,
        time: int | None = None,
        client: str | None = None,
        server: bool = False,
        one_off: bool = False,
        interval: int | None = None,
        udp: bool = False,
        **kwargs: dict[str, Any],
    ) -> ExecResult:
        """This is a wrapper for iperf3 which used for the network performance estimation.

        Args:
            port: Server port to listen on/connect to.
            time: Test duration in seconds.
            client: Run in client mode.
            server: Run in server mode.
            one_off: Handle one client connection then exit.
            interval: Seconds between periodic throughput reports.
            udp: Use UDP rather than TCP.
            **kwargs: Command arguments in the free form with values.
        """
        if client and server:
            err_msg = "Both client and server cannot be set."
            raise ValueError(err_msg)
        if not client and not server:
            err_msg = "Both client and server cannot be unset."
            raise ValueError(err_msg)
        time_lower = 0
        time_upper = 86400
        if time and (time < time_lower or time > time_upper):
            err_msg = f"Test duration must be between {time_lower} and {time_upper} seconds."
            raise ValueError(err_msg)
        port_lower = 1
        port_upper = 65535
        if port < port_lower or port > port_upper:
            err_msg = f"Port number must be between {port_lower} and {port_upper} inclusive."
            raise ValueError(err_msg)
        if one_off and not server:
            err_msg = "One off mode can only be used in server mode."
            raise ValueError(err_msg)

        opts = [
            *create_opt("time", time),
            *create_opt("port", port),
            *create_opt("client", client),
            *create_opt("server", server),
            *create_opt("one-off", one_off),
            *create_opt("interval", interval),
            *create_opt("udp", udp),
            *add_flag("json"),
        ]
        return self(
            opts,
            **kwargs,
        )

    def install(self) -> ExecResult:
        """Install iperf3 via the system package manager."""
        if self.path:
            return ExecResult(
                cmd=(), stderr=f"{self.name} already has been installed.", returncode=0
            )
        return self._install_packages(["iperf"])

    @staticmethod
    def metrics_to_bmf(metrics: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
        result: dict[str, dict[str, dict[str, Any]]] = {}
        if "end" in metrics and "sum_sent" in metrics["end"]:
            sum_sent = metrics["end"]["sum_sent"]
            result["sum"] = {
                "seconds": {"value": sum_sent["seconds"]},
                "bytes": {"value": sum_sent["bytes"]},
                "bits_per_second": {"value": sum_sent["bits_per_second"]},
            }

        if "end" in metrics and "cpu_utilization_percent" in metrics["end"]:
            cpu = metrics["end"]["cpu_utilization_percent"]
            result["cpu_utilization_percent"] = {
                "host_total": {"value": cpu["host_total"]},
                "host_user": {"value": cpu["host_user"]},
                "host_system": {"value": cpu["host_system"]},
            }
        return result

    @staticmethod
    def metrics_to_json(metrics: str) -> Any:
        return json.loads(metrics)
