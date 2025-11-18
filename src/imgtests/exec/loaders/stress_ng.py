from typing import Any, NamedTuple

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient
from imgtests.exec.utils import add_flag, create_opt


class StressNGVerifications(NamedTuple):
    always_enabled: tuple[str, ...]
    enabled_by_option: tuple[str, ...]
    not_implemented: tuple[str, ...]


class StressNg(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("stress-ng", ssh_client)

    def cpu_methods(self) -> tuple[str, ...] | None:
        result = self(["--cpu-method", "_which_"])
        # stress-ng exits with code 1 for this call
        if result.returncode != 1:
            return None
        return self.__parse_methods(result.stderr)

    def vm_methods(self) -> tuple[str, ...] | None:
        result = self(["--vm-method", "_which_"])
        # stress-ng exits with code 1 for this call
        if result.returncode != 1:
            return None
        return self.__parse_methods(result.stderr)

    def verifiable(self) -> StressNGVerifications | None:
        """Returns stressors that always enable verification or by option or not implements."""
        result = self(["--verifiable"])
        if result.returncode:
            return None
        always_enabled: tuple[str, ...] = ()
        enabled_by_option: tuple[str, ...] = ()
        not_implemented: tuple[str, ...] = ()
        for block in result.stdout.split("\n\n"):
            lines = block.strip().split("\n")
            header = lines[0].strip()
            items = " ".join(lines[1:]).strip().split()
            if header.startswith("Verification always enabled"):
                always_enabled = tuple(items)
            elif header.startswith("Verification enabled by --verify option"):
                enabled_by_option = tuple(items)
            elif header.startswith("Verification not implemented"):
                not_implemented = tuple(items)
        return StressNGVerifications(always_enabled, enabled_by_option, not_implemented)

    def run(  # noqa: PLR0913
        self,
        timeout_sec: int = 0,
        cpu: int | None = None,
        cpu_method: str = "all",
        vm: int | None = None,
        vm_method: str = "all",
        vm_bytes: str | None = None,
        iomix: int | None = None,
        iomix_bytes: str | None = None,
        verify: bool = True,
        **kwargs: dict[str, Any],
    ) -> ExecResult:
        """Runs the stress-ng util stressors.

        Args:
            timeout_sec (int): Execution time of stressors work. When set to 0 run 1 day
              stress test.
            cpu (int | None): Count of the CPU stressors. When set to 0 got count of logical
              processors.
            cpu_method (str): Stress CPU method.
            vm (int | None): Count of the virtual memory stressors. When set to 0 got count
              of logical processors.
            vm_method (str): Stress virtual memory method.
            vm_bytes (str | None): Utilized memory as value or percent of all available memory.
            iomix (int | None): Count of the I/O stressors. When set to 0 got count of logical
              processors.
            iomix_bytes (str | None): Utilized memory as value or percent of all available memory.
            verify (bool): Verify results if can.
            **kwargs (dict[str, Any]): Command arguments in the free form with values.

        Raises:
            ValueError: When invalid parameters provided or repeated.

        Returns:
            ExecResult: Result of the stress test work.
        """
        if timeout_sec < 0:
            err_msg = f"Invalid timeout '{timeout_sec}'. Expected more or equal 0."
            raise ValueError(err_msg)
        if cpu is not None and cpu < 0:
            err_msg = f"Invalid CPU count '{cpu}'. Expected more or equal 0."
            raise ValueError(err_msg)
        if vm is not None and vm < 0:
            err_msg = f"Invalid vm count '{vm}'. Expected more or equal 0."
            raise ValueError(err_msg)
        if iomix is not None and iomix < 0:
            err_msg = f"Invalid iomix count '{iomix}'. Expected more or equal 0."
            raise ValueError(err_msg)

        return self(
            [
                *create_opt("timeout", timeout_sec),
                *create_opt("cpu", cpu),
                *create_opt("cpu-method", cpu_method),
                *create_opt("vm", vm),
                *create_opt("vm-method", vm_method),
                *create_opt("vm-bytes", vm_bytes),
                *create_opt("iomix", iomix),
                *create_opt("iomix-bytes", iomix_bytes),
                *create_opt("verify", verify),
                *add_flag("metrics"),
            ],
            **kwargs,
        )

    def __parse_methods(self, raw_methods: str) -> tuple[str, ...] | None:
        try:
            methods = raw_methods.split(":", maxsplit=1)[1]
        except IndexError:
            return None
        return tuple(methods.strip().split())
