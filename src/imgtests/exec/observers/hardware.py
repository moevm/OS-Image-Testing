from typing import TYPE_CHECKING

from imgtests.exec.utils import add_flag, create_opt, extract_version

if TYPE_CHECKING:
    from imgtests.exec.exec import ExecResult, SSHClient
    from imgtests.types import Version
from imgtests.exec.base_util import BaseTestUtil, GenericUtil


class Lsblk(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("lsblk", ssh_client)


class Lshw(BaseTestUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("lshw", ssh_client)

    def run(
        self,
        class_: str | None = None,
        json: bool = False,
        xml: bool = False,
        html: bool = False,
        short: bool = False,
    ) -> ExecResult:
        """Calls lshw util for getting list hardware.

        Args:
            class_ (str | None, optional): Show the given class of hardware.
            json (bool, optional): Outputs the device tree as a JSON. Defaults to False.
            xml (bool, optional): Outputs the device tree as a XML. Defaults to False.
            html (bool, optional): Outputs the device tree as a HTML. Defaults to False.
            short (bool, optional): Outputs the device tree in a short format. Defaults to False.

        Returns:
            ExecResult: Result of the execution.
        """
        cmd: list[str] = [*create_opt("class", class_, use_one_dash=True)]
        if sum([json, xml, html, short]) > 1:
            err_msg = "Only one of json, xml, html or short can be used."
            raise ValueError(err_msg)

        if json:
            cmd.extend(add_flag("json", use_one_dash=True))
        if xml:
            cmd.extend(add_flag("xml", use_one_dash=True))
        if html:
            cmd.extend(add_flag("html", use_one_dash=True))
        if short:
            cmd.extend(add_flag("short", use_one_dash=True))

        return super().__call__(cmd)

    def version(self) -> Version | None:
        result = self(["-version"])
        if result.returncode:
            return None
        return extract_version(result.stdout.strip())
