from typing import TYPE_CHECKING, NamedTuple

from imgtests.exec.base_util import GenericUtil

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient


class BootTimeInfo(NamedTuple):
    firmware_time: float
    loader_time: float
    initrd_time: float
    kernel_time: float
    userspace_time: float
    total_time: float


class SlowService(NamedTuple):
    service_name: str
    slow_time_s: float


class SystemdAnalyze(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("systemd-analyze", ssh_client)

    def time(self) -> BootTimeInfo:
        raw = self(["time"]).stdout.strip()

        # prefill configuration to avoid system misconfiguration
        res: dict[str, float] = {
            "firmware_time": -1.0,
            "loader_time": -1.0,
            "initrd_time": -1.0,
            "kernel_time": -1.0,
            "userspace_time": -1.0,
            "total_time": -1.0,
        }

        # fill result dict with _parse_time result
        times = self._parse_time(raw)
        for pair in times.items():
            res[pair[0]] = pair[1]

        return BootTimeInfo(**res)

    def slow_load_services(self) -> tuple[SlowService, ...]:
        mins_and_secs = 2
        res: list[SlowService] = []
        tmp = self(["critical-chain"]).stdout.split("\n")[3:]

        for line in tmp:
            tmp_line = line.strip().replace("└─", "")
            plus_idx = tmp_line.find("+")
            # check if it is service and it is slow
            if ".service" in tmp_line and plus_idx != -1 and tmp_line[-2:] != "ms":
                service = tmp_line.split()[0]
                marks = tmp_line[plus_idx + 1 :].replace("s", "").replace("min", "|").split("|")
                if len(marks) == mins_and_secs:
                    slow_time = int(marks[0]) * 60 + float(marks[1])
                else:
                    slow_time = float(marks[0])
                res.append(SlowService(service_name=service, slow_time_s=slow_time))

        return tuple(sorted(res, key=lambda slow_service: slow_service.slow_time_s))

    @staticmethod
    def _parse_time(line: str) -> dict[str, float]:
        """Method to parse systemd-analyze time stdout line to a dict.

        stdout line example:
            'Startup finished in 2.871s \
             (firmware) + 2.349s (loader) + 2.640s (kernel) + 8.371s (userspace) = 16.231s
             graphical.target reached after 8.346s in userspace.'

        Attributes:
            line (str): systemd-analyze time stdout line.
        """
        parts_line = line.replace("=", "+").replace("Startup finished in ", "").replace(" ", "")
        parts = parts_line.split("\n")[0].split("+")
        res: dict[str, float] = {}

        # part time cases:
        # 1 - <M>min<S>.<Ms>s(<part name>)
        # 2 - <M>min<Ms>ms(<part name>)
        # 3 - <S>.<Ms>s(<part name>)
        # 4 - <Ms>ms(<part name>)
        # total time has no (<part name>)
        for part in parts:
            bracket_idx = part.find("(")
            key = part[bracket_idx + 1 : -1] + "_time"
            # separate total time key from the others
            if bracket_idx == -1:
                key = "total_time"
                part_time = part
            else:
                part_time = part[:bracket_idx]
            # case 2
            if part_time[-2:] == "ms" and "min" in part_time:
                minutes, milliseconds = part_time[:-2].split("min")
                res[key] = int(minutes) * 60 + float(milliseconds) / 1000
            # case 4
            elif part_time[-2:] == "ms":
                res[key] = float(part_time[:-2]) / 1000
            # case 1
            elif "min" in part_time:
                minutes, seconds = part_time[:-1].split("min")
                res[key] = int(minutes) * 60 + float(seconds)
            # case 3
            else:
                res[key] = float(part_time[:-1])

        return res
