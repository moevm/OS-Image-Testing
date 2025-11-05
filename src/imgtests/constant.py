import re
from typing import Final

VER_PATTERN: Final[re.Pattern[str]] = re.compile(r"(\d+[.]?)+")
