from abc import ABC, abstractmethod

from imgtests.exec.exec import ExecResult, SSHClient, run_command, which
from imgtests.exec.utils import extract_version


class BaseTestUtil(ABC):
    """Base class for the test tools.

    This class provides a common interface for the test tools and handles
    basic initialization logic.

    Attributes:
        name (str): Name of the utility.
        ssh_client (SSHClient | None): Client to the remote.
        path (str | None): Path to the utility executable.
    """

    def __init__(self, name: str, ssh_client: SSHClient | None = None) -> None:
        self.name = name
        self.ssh_client = ssh_client
        self.path = which(self.name, ssh_client)

    def __call__(self, cmd: list[str] | None = None) -> ExecResult:
        """Executes the utility with the provided command.

        Args:
            cmd (list[str] | None): Command arguments to pass to the utility.

        Returns:
            ExecResult: Result of the execution.
        """
        if cmd is None:
            cmd = []
        if self.path is None:
            return ExecResult(
                cmd=f"which {self.name}", stderr=f"Failed to locate '{self.name}'.", returncode=1
            )
        if self.ssh_client is None:
            return run_command([str(self.path), *cmd])
        return self.ssh_client(" ".join([str(self.path), *cmd]))

    def install(self) -> ExecResult:
        """Installs the utility.

        Raises:
            NotImplementedError: If the installation logic is not implemented
                for the specific utility.

        Returns:
            ExecResult: Execution result of the installation operation.
        """
        not_implemented_message = f"The '{self.name}' install logic is not implemented."
        raise NotImplementedError(not_implemented_message)

    @abstractmethod
    def version(self) -> str | None:
        """Returns the utility version.

        Returns:
            str | None: Version of the util or None if can't get.
        """
        ...


class GenericUtil(BaseTestUtil):
    def version(self) -> str | None:
        result = self(["--version"])
        if result.returncode:
            return None
        return extract_version(result.stdout.strip())
