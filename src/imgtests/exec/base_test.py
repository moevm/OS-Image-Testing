from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict

JsonType = Dict[str, Any]


class BaseTestResults(ABC):
    """Base interface for test results that can be collected and saved as JSON."""

    @abstractmethod
    def collect(self) -> None:
        """Collect test results and store them in the instance."""
        ...

    @abstractmethod
    def to_dict(self) -> JsonType:
        """Return normalized test results suitable for JSON serialization."""
        ...

    def save_json(self, path: str | Path) -> None:
        """Save test results as a JSON file using `to_dict()`."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

