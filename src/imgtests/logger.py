import logging
import sys
from pathlib import Path
from typing import Self, TextIO


class StreamFormatter(logging.Formatter):
    def __init__(self: Self) -> None:
        self._level_fmt = "[%(levelname)s]"
        self._log_fmt = " %(asctime)s - %(message)s"
        super().__init__(datefmt="%H:%M")

    def format(self: Self, record: logging.LogRecord) -> str:
        self._style._fmt = self._level_fmt + self._log_fmt

        return super().format(record)


def get_file_handler(filename: Path) -> logging.FileHandler:
    log_format = (
        "%(asctime)s - [%(levelname)s] - %(name)s - "
        "(%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"
    )
    file_handler = logging.FileHandler(filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            fmt=log_format,
            datefmt="%b %-d %T",
        )
    )

    return file_handler


def get_stderr_handler() -> logging.StreamHandler[TextIO]:
    stderr_handler = logging.StreamHandler(stream=sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(StreamFormatter())

    return stderr_handler


def get_stdout_handler() -> logging.StreamHandler[TextIO]:
    class STDOutFilter(logging.Filter):
        def filter(self: Self, record: logging.LogRecord) -> bool:
            return record.levelno in [logging.INFO, logging.DEBUG]

    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(STDOutFilter())
    stdout_handler.setFormatter(StreamFormatter())

    return stdout_handler


def set_handlers(logger: logging.Logger, filename: Path, log_level: str = "info") -> None:
    levelno = getattr(logging, log_level.upper())
    logger.setLevel(levelno)
    logger.addHandler(get_file_handler(filename))
    if levelno in [logging.INFO, logging.DEBUG]:
        logger.addHandler(get_stdout_handler())
    logger.addHandler(get_stderr_handler())
