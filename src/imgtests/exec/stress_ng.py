from imgtests.exec.exec import ExecResult, run_command, which


class StressNg:
    def __init__(self) -> None:
        self.name = "stress-ng"
        self.path = which(self.name)

    def __call__(self, cmd: list[str] | None = None) -> ExecResult:
        if cmd is None:
            cmd = []
        if self.path is None:
            return ExecResult(stderr=f"Failed to locate '{self.name}'.", returncode=1)
        return run_command([str(self.path), *cmd])

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
