from imgtests.exec.atutil import BaseTestUtil
from imgtests.exec.exec import SSHClient


class StressNg(BaseTestUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("stress-ng", ssh_client)

    def cpu_methods(self) -> tuple[str, ...] | None:
        result = self(["--cpu-method", "which"])
        # stress-ng exits with code 1 for this call
        if result.returncode != 1:
            return None
        try:
            # stress-ng logs into stderr for this call
            cpu_methods = result.stderr.split(":", maxsplit=1)[1]
        except IndexError:
            return None
        return tuple(cpu_methods.strip().split())
