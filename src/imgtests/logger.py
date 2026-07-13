import json
import logging
import re
import sys
from pathlib import Path
from typing import Literal, Self, TextIO

from pythonjsonlogger.json import JsonFormatter

from imgtests.constant import LIB_DATA_DIR

LogLevel = Literal["debug", "info", "warning", "error", "critical"]


class StreamFormatter(logging.Formatter):
    def __init__(self: Self) -> None:
        self._level_fmt = "[%(levelname)s]"
        self._log_fmt = " %(asctime)s - %(message)s"
        super().__init__(datefmt="%H:%M:%S")

    def format(self: Self, record: logging.LogRecord) -> str:
        self._style._fmt = self._level_fmt + self._log_fmt  # noqa: SLF001

        return super().format(record)


class ProgressHandle(logging.Handler):
    task_state_started = "RUNNING"
    task_started_pattern = r"Task id=([\w-]+) path=[\w|\.]+ state=(\w+)"
    tests_count_pattern = r"Total amount of tests per run: (\d+)"
    test_runs_pattern = r"Starting test run (\d+) of (\d+)"
    default_test_start_pattern = r"Starting '(.*\.)'.*"
    default_test_finish_pattern = r"'(.*\.)' test finished."
    suite_start_pattern = r"Running suite (.*)\."
    profiled_test_start_pattern = r"\[PLAN\] run stage=([\w-]+) tool=([\w-]+) subsystem=([\w-]+).*"
    profiled_test_finish_pattern = r"\[PLAN\] done .*"
    profile_done_pattern = r"\[PROFILED\] DONE profile=(\w+) pattern=(\w+) .*"
    progress_template = {  # noqa: RUF012
        "total_test_count": 0,
        "test_count": 0,
        "total_run_count": 0,
        "current_test_run": 0,
        "current_suite": "Not starter yet",
        "last_profile_done": "Not done yet",
        "current_test": "Not starter yet",
    }

    def __init__(self, level: logging._Level = logging.DEBUG):
        super().__init__(level)
        self.progress_data = {}
        self.proc_to_task = {}

    def emit(self, record: logging.LogRecord):  # noqa: PLR0915
        proc = str(record.process)
        msg = self.format(record)

        # detect task starterd or finished
        match = re.search(self.task_started_pattern, msg)
        if match:
            task_id = match.group(1)
            status = match.group(2)
            # task started
            if status == self.task_state_started:
                self.proc_to_task[proc] = task_id
            # task finished or broke
            else:
                self.proc_to_task[proc] = None
            # flush progress_data for process
            self.progress_data[proc] = self.progress_template.copy()

        match = re.search(self.tests_count_pattern, msg)
        if match and self.progress_data[proc]:
            total = int(match.group(1))
            self.progress_data[proc]["total_test_count"] = total

        match = re.search(self.test_runs_pattern, msg)
        if match and self.progress_data[proc]:
            # set current run
            cur = int(match.group(1))
            total = int(match.group(2))
            self.progress_data[proc]["current_test_run"] = cur
            self.progress_data[proc]["total_run_count"] = total
            # reset tests count
            self.progress_data[proc]["test_count"] = 0

        # default runner matches
        match = re.search(self.suite_start_pattern, msg)
        if match and self.progress_data[proc]:
            suite = match.group(1)
            self.progress_data[proc]["current_suite"] = suite

        match = re.search(self.default_test_start_pattern, msg)
        if match and self.progress_data[proc]:
            test = match.group(1)
            self.progress_data[proc]["current_test"] = test

        match = re.search(self.default_test_finish_pattern, msg)
        if match and self.progress_data[proc]:
            self.progress_data[proc]["test_count"] += 1
            self.progress_data[proc]["current_test"] = "Not started yet"

        # profiled runner matches
        match = re.search(self.profile_done_pattern, msg)
        if match and self.progress_data[proc]:
            profile = "-".join([match.group(1), match.group(2)])
            self.progress_data[proc]["last_profile_done"] = profile

        match = re.search(self.profiled_test_start_pattern, msg)
        if match and self.progress_data[proc]:
            subsystem = match.group(3)
            profile = match.group(1)
            tool = match.group(2)
            self.progress_data[proc]["current_test"] = f"{subsystem}-{profile} via {tool}"

        match = re.search(self.profiled_test_finish_pattern, msg)
        if match and self.progress_data[proc]:
            self.progress_data[proc]["test_count"] += 1
            self.progress_data[proc]["current_test"] = "Not started yet"

        if proc in self.proc_to_task and self.proc_to_task[proc] is not None:
            task_id = self.proc_to_task[proc]
            with Path.open(
                LIB_DATA_DIR / (task_id + "_progress.log"),
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(self.progress_data[proc], file, indent=4)


def set_handlers(
    logger: logging.Logger,
    filename: Path,
    log_level: LogLevel = "info",
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
    logger.addHandler(__get_progress_handler())
    logger.addHandler(__get_file_handler(filename))
    if levelno in [logging.INFO, logging.DEBUG]:
        logger.addHandler(__get_stdout_handler())
    logger.addHandler(__get_stderr_handler())


def __get_file_handler(filename: Path) -> logging.FileHandler:
    file_handler = logging.FileHandler(filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        JsonFormatter(
            ["asctime", "levelname", "name", "process", "thread", "message", "filename", "lineno"],
        ),
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


def __get_progress_handler() -> ProgressHandle:
    progress_handle = ProgressHandle()
    progress_handle.setLevel(logging.DEBUG)
    progress_handle.setFormatter(StreamFormatter())
    progress_handle.set_name("progress_handler")

    return progress_handle
