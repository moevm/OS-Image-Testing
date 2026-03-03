from typing import TYPE_CHECKING

from imgtests.exec.base_util import BaseTestUtil
from imgtests.exec.utils import extract_version

if TYPE_CHECKING:
    from imgtests.exec.exec import ExecResult, SSHClient


class Sar(BaseTestUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("sar", ssh_client)

    def version(self):
        result = self(["-V"])
        if result.returncode:
            return None
        return extract_version(result.stdout.strip())

    def run(self, interval: int | None = None, count: int | None = None) -> ExecResult:
        if interval is None and count is not None:
            err_msg = "If interval is None, count should be set None."
            raise ValueError(err_msg)

        if interval is not None and interval < 0:
            err_msg = f"Invalid interval '{interval}'. Expected more or equal 0."
            raise ValueError(err_msg)

        if interval is not None and interval == 0 and count is not None:
            err_msg = "If interval is '0', count should not be set."
            raise ValueError(err_msg)

        if interval is not None and interval != 0 and count is None:
            err_msg = "If interval is not equal 0, count should not be None."
            raise ValueError(err_msg)

        if count is not None and count <= 0:
            err_msg = f"Invalid count '{count}'. Expected more than 0."
            raise ValueError(err_msg)

        # create command
        opts = ["-B"]
        if interval is not None:
            opts.append(interval)
            if interval != 0 and count is not None:
                opts.append(count)

        return self(opts)
