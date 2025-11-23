import logging
import os
import sys
from pathlib import Path
from typing import NoReturn, TypeVar, cast

T = TypeVar("T")


def env_var_to_type_or_exit[T](variable: str, val_type: type[T], logger: logging.Logger) -> T:
    try:
        return env_var_to_type(variable, val_type)
    except ValueError as err:
        error(str(err), logger=logger)


def env_var_to_type[T](variable: str, val_type: type[T]) -> T:
    if variable not in os.environ:
        err_msg = f"Environment variable '{variable}' not found."
        raise ValueError(err_msg)

    raw_value = os.environ[variable].strip()
    if val_type is bool:
        if raw_value.lower() in ("true", "1", "yes", "on"):
            return cast("T", val=True)
        if raw_value.lower() in ("false", "0", "no", "off"):
            return cast("T", val=False)
        err_msg = f"Can't convert '{raw_value}' to bool."
        raise ValueError(err_msg)
    if val_type in (int, float, Path, str):
        return val_type(raw_value)
    err_msg = f"Unsupported val_type='{val_type}' provided."
    raise ValueError(err_msg)


def error(*msgs: str, logger: logging.Logger) -> NoReturn:
    for msg in msgs:
        logger.error(msg)
    sys.exit(1)
