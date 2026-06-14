from typing import TYPE_CHECKING

from imgtests.exec.debugfs import change_fault_parameters
from imgtests.exec.exec import ExecResult, SSHClient
from imgtests.exec.osinfo import get_os_release
from imgtests.exec.pkgmgrs.zypper import Zypper

if TYPE_CHECKING:
    import logging
    from collections.abc import Iterable


class PkgMgrMixin:
    """Mixin with helper for installing packages via system package manager."""

    def _install_packages(self, packages: Iterable[str]) -> ExecResult:
        pkgs = [p for p in packages if p]
        if not pkgs:
            msg = "No packages specified for installation."
            return ExecResult(
                cmd=(str(getattr(self, "name", "")) or "pkg-install",),
                stdout="",
                stderr=msg,
                returncode=1,
            )

        os_id = get_os_release(getattr(self, "ssh_client", None)).id
        if os_id and "opensuse" in os_id:
            zypper = Zypper(ssh_client=getattr(self, "ssh_client", None), use_sudo=True)
            return zypper.install_packages(pkgs)

        name = getattr(self, "name", "<unknown>")
        msg = (
            f"Automatic installation for {name!r} "
            f"is not supported on this OS (detected ID: {os_id!r})."
        )
        return ExecResult(
            cmd=(str(name),),
            stdout="",
            stderr=msg,
            returncode=1,
        )


class FaultCleanupMixin:
    def cleanup(self, client: SSHClient | None, logger: logging.Logger) -> None:
        change_fault_parameters(client, 0, 1)
        logger.info("Cleaned fault parameters.")
        default_cleanup = getattr(super(), "cleanup", None)
        if default_cleanup:
            default_cleanup(client, logger)
