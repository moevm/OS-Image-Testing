import logging
import sys
from typing import NoReturn

from imgtests.environment import env_var_to_type


def env_var_to_type_or_exit[T](variable: str, val_type: type[T], logger: logging.Logger) -> T:
    try:
        return env_var_to_type(variable, val_type)
    except ValueError as err:
        error(str(err), logger=logger)


def error(*msgs: str, logger: logging.Logger) -> NoReturn:
    for msg in msgs:
        logger.error(msg)
    sys.exit(1)
