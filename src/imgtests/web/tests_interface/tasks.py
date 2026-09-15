from typing import Any, Final

from django.tasks import task

from imgtests.database.database import ImgtestsDatabase
from imgtests.runner import Runner, run_tests

DEFAULT_TASK_TIMEOUT_SEC: Final = 3600


@task()
def run_test_task(
    distro: str,
    mode: Runner = "default",
    test_runs_count: int = 1,
    config: dict[str, Any] | None = None,
) -> dict[str, str | int]:
    try:
        database = ImgtestsDatabase()
        connection = database.get_connection(distro)
        if connection is None:
            return {
                "status": "failed",
                "error": f"Connection for distribution '{distro}' not found.",
            }
        run_tests(
            distribution=connection,
            mode=mode,
            test_runs_count=test_runs_count,
            config=config,
        )
    except Exception as e:  # noqa: BLE001
        return {
            "status": "failed",
            "error": str(e),
        }
    else:
        return {
            "status": "completed",
            "output": "",
            "exit_code": 0,
            "stderr": "",
        }
