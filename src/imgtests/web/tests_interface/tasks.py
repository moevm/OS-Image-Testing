import subprocess
from typing import Final

from django.tasks import task

DEFAULT_TASK_TIMEOUT_SEC: Final = 3600


@task()
def run_test_task(env_vars: dict[str, str]) -> dict[str, str | int | bytes]:
    try:
        result = subprocess.run(
            ["/usr/bin/env", "python3", "/home/user/image/runner.py"],
            check=True,
            capture_output=True,
            text=True,
            timeout=DEFAULT_TASK_TIMEOUT_SEC,
            env=env_vars,
        )
    except subprocess.TimeoutExpired as e:
        return {
            "status": "failed",
            "error": f"Test timed out after {e.timeout} seconds",
            "output": e.stdout or "",
            "stderr": e.stderr or "",
        }
    except subprocess.CalledProcessError as e:
        return {
            "status": "failed",
            "error": str(e),
            "output": e.stdout,
            "stderr": e.stderr,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "status": "failed",
            "error": str(e),
        }
    else:
        return {
            "status": "completed",
            "output": result.stdout + (f"\n\nErrors:\n{result.stderr}" if result.stderr else ""),
            "exit_code": result.returncode,
            "stderr": result.stderr,
        }
