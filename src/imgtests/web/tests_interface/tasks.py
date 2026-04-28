import subprocess

from django.tasks import task


@task()
def run_test_task(env_vars: dict) -> dict:
    try:
        result = subprocess.run(
            ["/usr/bin/env", "python3", "/home/user/image/runner.py"],
            check=True,
            capture_output=True,
            text=True,
            timeout=3600,
            env=env_vars,
        )
        return {
            "status": "completed",
            "output": result.stdout + (f"\n\nErrors:\n{result.stderr}" if result.stderr else ""),
            "exit_code": result.returncode,
            "stderr": result.stderr,
        }
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
