from typing import TYPE_CHECKING

from imgtests.exec.base_util import GenericUtil

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from imgtests.exec.exec import SSHClient


class Zcat(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("zcat", ssh_client)

    def get_compressed_files_contents(self, files: Sequence[str | Path]) -> tuple[str, ...]:
        return tuple(self([str(file) for file in files]).stdout.strip().split("\n"))
