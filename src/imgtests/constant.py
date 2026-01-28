import re
from pathlib import Path
from typing import Final

VER_PATTERN: Final[re.Pattern[str]] = re.compile(r"(\d+[.]?)+")
LIB_NAME: Final = "imgtests"
LOG_PATH: Final[Path] = Path.home() / LIB_NAME / "processing.log"
