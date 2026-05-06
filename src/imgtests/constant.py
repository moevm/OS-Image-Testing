import re
from typing import Final

from imgtests.types import TestResult, TestStatus

VER_PATTERN: Final[re.Pattern[str]] = re.compile(r"(\d+[.]?)+")
LIB_NAME: Final = "imgtests"
SSH_CLIENT_MISSING_RESULT: Final = TestResult(
    status=TestStatus.BROKEN,
    # TODO: use frozendict from 3.15
    metrics={"error": "SSH client is not provided"},
)
