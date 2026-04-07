from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from imgtests.exec.exec import ExecResult, SSHClient, common_run_command, which
from imgtests.exec.utils import extract_version, kwargs_to_cmd_args

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from imgtests.types import Version


class BaseTestUtil(ABC):
    """Base class for the test tools.

    This class provides a common interface for the test tools and handles
    basic initialization logic.

    Attributes:
        name (str): Name of the utility.
        ssh_client (SSHClient | None): Client to the remote.
        path (str | None): Path to the utility executable.
    """

    def __init__(
        self,
        name: str,
        ssh_client: SSHClient | None = None,
        use_sudo: bool = False,
    ) -> None:
        self.name = name
        self.ssh_client = ssh_client
        self.use_sudo = use_sudo
        self.path = which(self.name, ssh_client, use_sudo=use_sudo)

    def __call__(
        self,
        cmd: Sequence[str | Path] | None = None,
        log_errors: bool = True,
        **kwargs: dict[str, Any],
    ) -> ExecResult:
        """Executes the utility with the provided command.

        Args:
            cmd (Sequence[str | Path] | None): Command arguments to pass to the utility.
            log_errors (bool): Show or hide error messages in the logs.
            **kwargs (dict[str, Any]): Command arguments in the free form with values.

        Raises:
            ValueError: When parameters repeated.

        Returns:
            ExecResult: Result of the execution.
        """
        if cmd is None:
            cmd = []
        if self.path is None:
            return ExecResult(
                cmd=("which", self.name), stderr=f"Failed to locate '{self.name}'.", returncode=1
            )
        for k in kwargs:
            if k in cmd:
                err_msg = f"Argument '{k}' is already set."
                raise ValueError(err_msg)
        final_cmd = [str(self.path), *(str(arg) for arg in cmd), *kwargs_to_cmd_args(**kwargs)]
        if self.use_sudo:
            final_cmd = ["sudo", *final_cmd]
        return common_run_command(final_cmd, self.ssh_client, log_errors=log_errors)

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

    @staticmethod
    def metrics_to_json(metrics: Any) -> Any:
        """Converts the metrics provided by the utility into JSON.

        Args:
            metrics (Any): Metrics in the format provided by the specific utility.

        Returns:
            str: JSON like object.
        """
        return metrics

    @staticmethod
    def metrics_to_bmf(metrics: Any) -> Any:
        """Converts the metrics provided by the utility into BMF."""
        return metrics

    def prepare(self) -> ExecResult:
        """Prepare before running the utility, if necessary."""
        return ExecResult((), "", "", 0)

    @abstractmethod
    def version(self) -> Version | None:
        """Returns the utility version.

        Returns:
            str | None: Version of the util or None if can't get.
        """
        ...


class GenericUtil(BaseTestUtil):
    def version(self) -> Version | None:
        result = self(["--version"])
        if result.returncode:
            return None
        return extract_version(result.stdout.strip())
