from imgtests.exec.base_util import BaseTestUtil
from imgtests.exec.exec import SSHClient


class Perf(BaseTestUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("perf", ssh_client)
