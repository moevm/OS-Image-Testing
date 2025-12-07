from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from imgtests.exec.base_util import GenericUtil
from imgtests.exec.exec import ExecResult, SSHClient, run_command

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

logger = logging.getLogger(__name__)


class Zypper(GenericUtil):
    """Wrapper around the zypper package manager, working over SSH or locally."""

    def __init__(
        self,
        ssh_client: SSHClient | None = None,
        use_sudo: bool = False,
    ) -> None:
        super().__init__("zypper", ssh_client)
        self.use_sudo = use_sudo

    def _build_args(self, args: Sequence[str]) -> list[str]:
        """Build zypper arguments with common parameters."""
        return ["--non-interactive", *args]

    def _run(self, args: Sequence[str]) -> ExecResult:
        """Run a zypper command on a remote or local machine."""
        base_args = self._build_args(args)

        if not self.use_sudo:
            return self(base_args)

        if self.path is None:
            return ExecResult(
                cmd=f"which {self.name}",
                stdout="",
                stderr=f"Failed to locate '{self.name}'.",
                returncode=1,
            )

        cmd_list = ["sudo", str(self.path), *base_args]
        cmd_str = " ".join(cmd_list)

        if self.ssh_client is None:
            return run_command(cmd_list)

        return self.ssh_client(cmd_str)

    def refresh(self) -> ExecResult:
        """Refresh repository metadata (zypper refresh)."""
        logger.info("Refreshing zypper repositories...")
        result = self._run(["refresh"])
        if result.returncode:
            logger.error("zypper refresh failed: %s", result.stderr)
        return result

    def install(self, packages: Iterable[str]) -> ExecResult:
        """Install one or more packages via zypper install."""
        pkgs = [p for p in packages if p]
        if not pkgs:
            msg = "No packages specified for installation."
            logger.error(msg)
            return ExecResult(
                cmd="zypper install",
                stdout="",
                stderr=msg,
                returncode=1,
            )

        refresh_result = self.refresh()
        if refresh_result.returncode:
            return refresh_result

        args = [
            "install",
            "--auto-agree-with-licenses",
            "--no-confirm",
            *pkgs,
        ]
        logger.info("Installing packages via zypper: %s", ", ".join(pkgs))
        result = self._run(args)

        if result.returncode == 0:
            logger.info("Successfully installed packages: %s", ", ".join(pkgs))
        else:
            logger.error(
                "Failed to install packages via zypper: %s. Stderr: %s",
                ", ".join(pkgs),
                result.stderr,
            )
        return result

    def is_installed(self, package: str) -> bool:
        """Check whether a package is installed."""
        logger.info("Checking if package '%s' is installed via zypper.", package)
        result = self._run(["se", "--installed-only", "--match-exact", package])
        if result.returncode != 0:
            return False
        return package in result.stdout
