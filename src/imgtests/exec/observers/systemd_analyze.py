from typing import NamedTuple
from imgtests.exec.exec import SSHClient
from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import SSHClient


class BootTimeInfo(NamedTuple):
    firmware_time:  float
    loader_time:    float
    initrd_time:    float
    kernel_time:    float
    userspace_time: float
    total_time:     float


class SystemdAnalyze(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("systemd-analyze", ssh_client)
    
    def boot_time(self) -> BootTimeInfo:
        mins_and_secs = 2
        raw = self(["time"]).stdout.strip()
        raw = raw.replace("=", "+").replace("Startup finished in ", "").replace(" ", "")
        ret_args = raw.split("+")

        # prefill configuration to avoid system missconfiguration
        res: dict[str, float] = {
            "firmware_time":  -1.0,
            "loader_time":    -1.0,
            "initrd_time":    -1.0,
            "kernel_time":    -1.0,
            "userspace_time": -1.0,
            "total_time":     -1.0
        }

        # parse time signatures
        for line in ret_args:
            key = line[line.find("(") + 1:-1] + "_time"
            # separate total time key from the others
            if (line.find("(") == -1):
                key = "total_time"
            el = line[:line.find("(")].replace("s", "").replace("min", "|").split('|')

            if len(el) == mins_and_secs:
                res[key] = int(el[0]) * 60 + float(el[1])
            else:
                res[key] = float(el[0])
        
        return BootTimeInfo(**res)

    def slow_load_services(self) -> dict[str, float]:
        mins_and_secs = 2
        res: dict[str, float] = {}
        tmp = self(['critical-chain']).stdout.split('\n')[3:]

        for line in tmp:
            el = line.strip().replace('└─', '')
            # check if service and it is slow
            if "service" in el and el.find('+') >= 0 and el[-2:] != "ms":
                service = el.split()[0]
                el = el[el.find('+') + 1:].replace("s", "").replace("min", "|").split('|')
                if len(el) == mins_and_secs:
                    res[service] = int(el[0]) * 60 + float(el[1])
                else:
                    res[service] = float(el[0])
                res = dict(sorted(res.items(), key=lambda item: item[1], reverse=True))
        return res
