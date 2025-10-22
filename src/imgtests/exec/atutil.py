from abc import ABC, abstractmethod

from imgtests.exec.exec import ExecResult, which


class AbstractUtil(ABC):
    """Abstract base class for the test tools.

    This class provides a common interface for the test tools and handles
    basic initialization logic.

    Attributes:
        name (str): Name of the utility.
        path (str | None): Path to the utility executable.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.path = which(self.name)

    @abstractmethod
    def __call__(self, cmd: list[str] | None = None) -> ExecResult:
        """Executes the utility with the provided command.

        Args:
            cmd (list[str] | None): Command arguments to pass to the utility.

        Returns:
            ExecResult: Result of the execution.
        """
        ...

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
