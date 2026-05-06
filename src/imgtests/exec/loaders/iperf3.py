import json
from concurrent.futures import TimeoutError as FutureTimeoutError
from time import monotonic, sleep
from typing import TYPE_CHECKING, Any, Final

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, common_run_command
from imgtests.exec.pkgmgrs.mixin import PkgMgrMixin
from imgtests.exec.utils import add_flag, create_opt
from imgtests.results_adapter import AdapterResult

if TYPE_CHECKING:
    from concurrent.futures import Future, ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


class Iperf3(PkgMgrMixin, GenericUtil):
    # Give the iperf3 server a small buffer to bind the socket and start accepting clients.
    IPERF3_SERVER_STARTUP_SEC: Final = 3
    # Wait briefly for the one-off iperf3 server to exit after the client finishes.
    IPERF3_SERVER_SHUTDOWN_TIMEOUT_SEC: Final = 2
    IPERF3_LOCAL_SERVER_SHUTDOWN_TIMEOUT_SEC: Final = 5

    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("iperf3", ssh_client)

    def stop_server(self) -> ExecResult:
        return common_run_command(["pkill", "-f", "iperf3.*--server"], self.ssh_client)

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
                cmd=(),
                stderr=f"{self.name} already has been installed.",
                returncode=0,
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

    @staticmethod
    def bundle_metrics_to_json(
        client_result: ExecResult,
        server_result: ExecResult,
    ) -> dict[str, Any]:
        return {
            "client": Iperf3.metrics_to_json(client_result.stdout.strip()),
            "server": Iperf3.metrics_to_json(server_result.stdout.strip()),
        }

    @staticmethod
    def split_result(
        raw_metrics: dict[str, Any],
        test_index: int = 0,  # noqa: ARG004
    ) -> AdapterResult:
        if not raw_metrics:
            return AdapterResult(
                tool="iperf3",
                test_type={},
                time={},
                metrics={},
            )

        client_metrics = raw_metrics.get("client", {})
        server_metrics = raw_metrics.get("server", {})
        test_info = client_metrics.get("start", {}).get("test_start", {})

        test_type = {"protocol": test_info.get("protocol", "unknown")}
        time = {"duration_sec": float(test_info.get("duration", 0.0))}

        metrics = {
            "client": {
                "start": client_metrics.get("start", {}),
                "intervals": client_metrics.get("intervals", []),
                "end": client_metrics.get("end", {}),
            },
            "server": {
                "start": server_metrics.get("start", {}),
                "intervals": server_metrics.get("intervals", []),
                "end": server_metrics.get("end", {}),
            },
        }

        return AdapterResult(
            tool="iperf3",
            test_type=test_type,
            time=time,
            metrics=metrics,
        )


class Iperf3Bundle:
    __slots__ = ("__client", "__server")

    def __init__(self, client: SSHClient | None = None, server: SSHClient | None = None) -> None:
        self.__client = Iperf3(client)
        self.__server = Iperf3(server)

    @property
    def client(self) -> Iperf3:
        return self.__client

    @property
    def server(self) -> Iperf3:
        return self.__server

    def start_server(
        self,
        executor: ThreadPoolExecutor,
    ) -> Future[ExecResult]:
        server_future = executor.submit(
            self.server.run,
            server=True,
            one_off=True,
            version4=True,
        )
        sleep(Iperf3.IPERF3_SERVER_STARTUP_SEC)
        return server_future

    def wait_server(
        self,
        server_future: Future[ExecResult],
        timeout: float,
    ) -> ExecResult:
        try:
            return server_future.result(timeout=max(0.0, timeout))
        except FutureTimeoutError:
            self.server.stop_server()
            raise

    @staticmethod
    def server_wait_timeout(
        deadline: float,
        max_timeout_sec: float = Iperf3.IPERF3_SERVER_SHUTDOWN_TIMEOUT_SEC,
    ) -> float:
        return max(0.0, min(max_timeout_sec, deadline - monotonic()))
