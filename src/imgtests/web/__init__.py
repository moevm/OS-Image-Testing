import os
import sys
from pathlib import Path

from django.core.management import execute_from_command_line


def run_django() -> None:
    app_path = Path(__file__).parent
    sys.path.insert(0, str(app_path))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

    execute_from_command_line(sys.argv)
