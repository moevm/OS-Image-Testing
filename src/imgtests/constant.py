import re
from pathlib import Path
from typing import Final

from imgtests.types import TestResult, TestStatus

VER_PATTERN: Final[re.Pattern[str]] = re.compile(r"(\d+[.]?)+")
LIB_NAME: Final = "imgtests"
# Paths
LOG_PATH: Final = Path.home() / LIB_NAME / "processing.log"
METADATA_FILE: Final = Path.home() / LIB_NAME / "test_suites_metadata.yml"
CONFIG_DIR: Final = Path.home() / LIB_NAME / "test_configs"

SSH_CLIENT_MISSING_RESULT: Final = TestResult(
    status=TestStatus.BROKEN,
    # TODO: use frozendict from 3.15
    metrics={"error": "SSH client is not provided"},
)
