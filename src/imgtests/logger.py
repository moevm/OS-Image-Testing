import logging
import sys
from pathlib import Path
from typing import Literal, Self, TextIO

from pythonjsonlogger.json import JsonFormatter


class StreamFormatter(logging.Formatter):
    def __init__(self: Self) -> None:
        self._level_fmt = "[%(levelname)s]"
        self._log_fmt = " %(asctime)s - %(message)s"
        super().__init__(datefmt="%H:%M:%S")

    def format(self: Self, record: logging.LogRecord) -> str:
        self._style._fmt = self._level_fmt + self._log_fmt  # noqa: SLF001

        return super().format(record)


def set_handlers(
    logger: logging.Logger,
    filename: Path,
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info",
) -> None:
    """Sets up logging handlers for the provided logger instance.

    This function configures the logging level, adds a file handler, and stderr
    handler and optionally adds stdout handler based on the log level.

    Args:
        logger (logging.Logger): The logger instance to configure.
        filename (Path): The file path where logs should be written.
        log_level (str): The logging level to set.

    Behavior:
        - Adds a file handler to write logs to the specified file in json format.
        - Adds a stdout handler if the log level is "info" or "debug".
        - Always adds a stderr handler for error logging.
    """
    levelno = getattr(logging, log_level.upper())
    logger.setLevel(levelno)
    logger.addHandler(__get_file_handler(filename))
    if levelno in [logging.INFO, logging.DEBUG]:
        logger.addHandler(__get_stdout_handler())
    logger.addHandler(__get_stderr_handler())


def __get_file_handler(filename: Path) -> logging.FileHandler:
    file_handler = logging.FileHandler(filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        JsonFormatter(
            ["asctime", "levelname", "name", "process", "thread", "message", "filename", "lineno"]
        )
    )

    return file_handler


def __get_stderr_handler() -> logging.StreamHandler[TextIO]:
    stderr_handler = logging.StreamHandler(stream=sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(StreamFormatter())

    return stderr_handler


def __get_stdout_handler() -> logging.StreamHandler[TextIO]:
    class STDOutFilter(logging.Filter):
        def filter(self: Self, record: logging.LogRecord) -> bool:
            return record.levelno in [logging.INFO, logging.DEBUG]

    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(STDOutFilter())
    stdout_handler.setFormatter(StreamFormatter())

    return stdout_handler
