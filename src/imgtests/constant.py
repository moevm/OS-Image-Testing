import re
from pathlib import Path
from typing import Final

from imgtests.types import TestResult, TestStatus

VER_PATTERN: Final[re.Pattern[str]] = re.compile(r"(\d+[.]?)+")
LIB_NAME: Final = "imgtests"
# Paths
LIB_DATA_DIR: Final = Path.home() / LIB_NAME
LOG_PATH: Final = LIB_DATA_DIR / "processing.log"
CONFIG_DIR: Final = LIB_DATA_DIR / "test_configs"
CONFIG_FILE: Final = LIB_DATA_DIR / "user_distros.json"
REPORTS_DIR: Final = LIB_DATA_DIR / "results"
EXCEL_REPORTS_DIR: Final = LIB_DATA_DIR / "excel_reports"

SSH_CLIENT_MISSING_RESULT: Final = TestResult(
    status=TestStatus.BROKEN,
    # TODO: use frozendict from 3.15
    metrics={"error": "SSH client is not provided"},
)

QEMU: Final = "qemu"
