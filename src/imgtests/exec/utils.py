from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from imgtests.constant import VER_PATTERN
from imgtests.types import Version

if TYPE_CHECKING:
    import re
    from collections.abc import Sequence


DEFAULT_TIMEOUT_KILL_AFTER_SEC = 30
TIMEOUT_RETURN_CODES = frozenset({124, 137})


def create_opt(
    key: str,
    value: Any | None,
    use_equals: bool = False,
    use_one_dash: bool = False,
) -> list[str]:
    """Create a command line option list from the given parameters.

    Args:
        key (str): Option name. Will be prefixed with '--' by default or '-' if
          `use_one_dash` is True.
        value (Any | None): Option value. Special handling:
          - None → empty list;
          - bool → [key] if True, else [];
          - Enum → uses .value attribute;
          - other types → converted to string.
        use_equals (bool, optional): If True, returns ["--<key>=<value>"].
          If False (default), returns [key, value] (e.g., ['--key', 'value']).
        use_one_dash (bool, optional): If True, uses single dash prefix ('-key') instead
          of double dash ('--key'). Default is False.

    Returns:
        list[str]: Command line option representation.

    Examples:
        >>> create_opt("verbose", True)
        ['--verbose']
        >>> create_opt("output", "file.txt")
        ['--output', 'file.txt']
        >>> create_opt("format", "json", use_equals=True)
        ['--format=json']
        >>> create_opt("debug", False)
        []
        >>> create_opt("count", None)
        []
        >>> create_opt("v", True, use_one_dash=True)
        ['-v']
        >>> create_opt("f", "config.ini", use_one_dash=True, use_equals=True)
        ['-f=config.ini']
    """
    if value is None:
        return []
    key = f"-{key}" if use_one_dash else f"--{key}"
    if isinstance(value, bool):
        return [key] if value else []
    value_str = str(value.value) if isinstance(value, Enum) else str(value)

    if use_equals:
        return [f"{key}={value_str}"]
    return [key, value_str]


def add_flag(key: str, use_one_dash: bool = False) -> list[str]:
    return create_opt(key=key, value=True, use_one_dash=use_one_dash)


def add_sudo(use_sudo: bool) -> list[str]:
    return ["sudo"] if use_sudo else []


def wrap_with_timeout(
    cmd: Sequence[str],
    timeout_sec: int,
    *,
    use_sudo: bool = False,
    kill_after_sec: int = DEFAULT_TIMEOUT_KILL_AFTER_SEC,
    verbose: bool = True,
) -> list[str]:
    """Wraps a command with GNU timeout.

    Args:
        cmd (Sequence[str]): Command to run under timeout.
        timeout_sec (int): Soft timeout in seconds.
        use_sudo (bool): Whether to run timeout via sudo.
        kill_after_sec (int): Seconds before sending SIGKILL after soft timeout.
        verbose (bool): Whether timeout should print diagnostic messages.

    Returns:
        list[str]: Command wrapped with timeout.
    """
    if timeout_sec <= 0:
        error_message = "timeout_sec must be positive."
        raise ValueError(error_message)

    verbose_args = add_flag("verbose") if verbose else []

    return [
        *add_sudo(use_sudo),
        "timeout",
        *verbose_args,
        *create_opt("kill-after", f"{kill_after_sec}s", use_equals=True),
        f"{timeout_sec}s",
        *(str(arg) for arg in cmd),
    ]


def is_timeout_returncode(returncode: int) -> bool:
    return returncode in TIMEOUT_RETURN_CODES


def extract_version(out: str, pattern: re.Pattern[str] = VER_PATTERN) -> Version | None:
    match = pattern.search(out)
    if match is None:
        return None
    return Version(match.group())


def kwargs_to_cmd_args(**kwargs: str | float | bool | None) -> list[str]:
    args: list[str] = []
    for k, w in kwargs.items():
        args.extend(create_opt(k, w))
    return args
