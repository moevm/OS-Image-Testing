import os
import sys
from pathlib import Path


def run_django():
    app_path = Path(__file__).parent
    sys.path.insert(0, str(app_path))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Can't import Django") from exc

    execute_from_command_line(sys.argv)
