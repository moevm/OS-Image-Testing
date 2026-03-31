import re
from contextlib import suppress
from enum import Enum
from functools import total_ordering
from typing import NamedTuple


@total_ordering
class Version:
    def __init__(self, version: str, base: int = 10) -> None:
        self.__version = re.sub(r"(\.0+)*$", "", version)
        version_parts: list[str | int] = []
        self.base = base
        for part in self.__version.split("."):
            converted_part = part
            try:
                converted_part = int(part, base=base)
            except ValueError:
                for sub_part in part.split("-"):
                    converted_part = sub_part
                    with suppress(ValueError):
                        converted_part = int(sub_part, base=base)
                    if converted_part != "":
                        version_parts.append(converted_part)
                continue
            version_parts.append(converted_part)
        self.__version_parts: tuple[str | int] = tuple(version_parts)

    def __str__(self) -> str:
        return self.version

    def __repr__(self) -> str:
        return f"Version(version={self.__version}, base={self.base})"

    def __hash__(self) -> int:
        return hash(self.__version_parts)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            err_msg = f"Can't compare Version with {type(other)}"
            raise TypeError(err_msg)
        return self.__version_parts == other.__version_parts

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            err_msg = f"Can't compare Version with {type(other)}"
            raise TypeError(err_msg)
        return self.__version_parts < other.__version_parts

    @property
    def version(self) -> str:
        str_parts: list[str] = []
        hex_base = 16
        for part in self.__version_parts:
            if self.base == hex_base:
                str_parts.append(f"{part:x}".upper())
            else:
                str_parts.append(str(part))
        return ".".join(str_parts)


class Distro(str, Enum):
    OPEN_SUSE_LEAP = "opensuse-leap"
    POKY = "poky"


class TestsCounts(NamedTuple):
    total_count: int = 0
    broken_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    skip_count: int = 0


class Subsystem(str, Enum):
    FILE = "file"
    IPC = "IPC"
    MEMORY = "memory"
    NETWORK = "network"
    SYSCALLS = "syscalls"
    SYSTEM = "system"
