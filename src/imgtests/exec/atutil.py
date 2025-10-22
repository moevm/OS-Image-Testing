from abc import ABC, abstractmethod

from imgtests.exec.exec import ExecResult, which


class AbstractUtil(ABC):
    def __init__(self, name: str) -> None:
        self.name = name
        self.path = which(self.name)

    @abstractmethod
    def __call__(self, cmd: list[str] | None = None) -> ExecResult: ...

    def install(self) -> ExecResult:
        not_implemented_message = f"The '{self.name}' install logic is not implemented."
        raise NotImplementedError(not_implemented_message)
