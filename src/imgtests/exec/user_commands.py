from typing import TYPE_CHECKING, Literal, NamedTuple

from imgtests.exec.exec import ExecResult
from imgtests.exec.pkgmgrs.mixin import PkgMgrMixin
from imgtests.exec.utils import add_flag, create_opt

if TYPE_CHECKING:
    from imgtests.exec.exec import SSHClient
from imgtests.exec.base_util import GenericUtil


class MkDir(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("mkdir", ssh_client)


class Touch(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None, use_sudo: bool = False) -> None:
        super().__init__("touch", ssh_client, use_sudo=use_sudo)


class Rm(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("rm", ssh_client)


class Dd(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("dd", ssh_client)


class Mdadm(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("mdadm", ssh_client)


class Nproc(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("nproc", ssh_client)


class Grep(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("grep", ssh_client)


class Times(NamedTuple):
    real: float
    user: float
    system: float


class Time(PkgMgrMixin, GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("time", ssh_client)

    def run(self, cmd: str) -> Times | None:
        result = self(["--format", "'%e %U %S'", cmd])
        if result.returncode:
            return None
        lines = result.stderr.splitlines()
        for line in lines:
            raw_time = line.split()
            try:
                return Times(float(raw_time[0]), float(raw_time[1]), float(raw_time[2]))
            except ValueError, IndexError:
                continue
        return None

    def install(self) -> ExecResult:
        """Install time via the system package manager."""
        if self.path:
            return ExecResult(
                cmd=(),
                stderr=f"{self.name} already has been installed.",
                returncode=0,
            )
        return self._install_packages(["time"])


SshKeyType = Literal["dsa", "ecdsa", "ecdsa-sk", "ed25519", "ed25519-sk", "rsa"]
FingerprintHash = Literal["md5", "sha256"]


class SshKeygen(GenericUtil):
    def __init__(self, ssh_client: SSHClient | None = None) -> None:
        super().__init__("ssh-keygen", ssh_client)

    def run(  # noqa: PLR0913
        self,
        filename: str | None = None,
        hostname: str | None = None,
        key_type: str | None = None,
        bits: int | None = None,
        fingerprint_hash: FingerprintHash | None = None,
        show_fingerprint: bool = False,
        passphrase: str | None = None,
    ) -> ExecResult:
        """Runs the ssh-keygen util.

        Args:
            filename (str | None, optional): The filename of the key file. Defaults to None.
            hostname (str | None, optional): Hostname for searching in a known_hosts file.
              Defaults to None.
            key_type (str | None, optional): The type of key to create. Defaults to None.
            bits (int | None, optional): The number of bits in the key to create. Defaults to None.
            fingerprint_hash (FingerprintHash | None, optional): The hash algorithm.
              Defaults to None.
            show_fingerprint (bool, optional): Show fingerprint of specified public key file.
              Defaults to False.
            passphrase (str | None, optional): The new passphrase. Defaults to None.

        Returns:
            ExecResult: Result of ssh-keygen work.
        """
        opts = [
            *create_opt("f", filename, use_one_dash=True),
            *create_opt("t", key_type, use_one_dash=True),
            *create_opt("b", bits, use_one_dash=True),
            *create_opt("E", fingerprint_hash, use_one_dash=True),
            *create_opt("F", hostname, use_one_dash=True),
            # TODO: use more secure way to pass passphrase
            *create_opt("N", passphrase, use_one_dash=True),
        ]
        if show_fingerprint:
            opts.extend(add_flag("l", use_one_dash=True))
        return self(opts)
