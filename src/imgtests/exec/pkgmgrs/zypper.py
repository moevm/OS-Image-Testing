from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from imgtests.exec.exec import ExecResult, SSHClient

logger = logging.getLogger(__name__)


@dataclass
class Zypper:
    """Wrapper around the zypper package manager, working over SSH."""

    ssh_client: SSHClient
    use_sudo: bool = False

    def _build_cmd(self, args: Sequence[str]) -> list[str]:
        """Build a zypper command with common parameters."""
        base_cmd: list[str] = ["zypper", "--non-interactive"]
        if self.use_sudo:
            base_cmd.insert(0, "sudo")
        return [*base_cmd, *args]

    def _run(self, args: Sequence[str]) -> ExecResult:
        """Run a zypper command on a remote machine."""
        cmd = self._build_cmd(args)
        return self.ssh_client(" ".join(cmd))

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
        logger.info(
            "Installing packages via zypper: %s",
            ", ".join(pkgs),
        )
        result = self._run(args)
        if result.returncode == 0:
            logger.info(
                "Successfully installed packages: %s",
                ", ".join(pkgs),
            )
        else:
            logger.error(
                "Failed to install packages via zypper: %s. Stderr: %s",
                ", ".join(pkgs),
                result.stderr,
            )
        return result

    def is_installed(self, package: str) -> bool:
        """Check whether a package is installed."""
        logger.info(
            "Checking if package '%s' is installed via zypper.",
            package,
        )
        result = self._run(
            ["se", "--installed-only", "--match-exact", package],
        )
        if result.returncode != 0:
            return False
        return package in result.stdout
