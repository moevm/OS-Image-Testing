import os
import subprocess
import threading
import uuid
from typing import TYPE_CHECKING

from django.http import HttpRequest, JsonResponse
from django.shortcuts import render

if TYPE_CHECKING:
    from django.http.response import HttpResponse


test_runs = {}


def _run_test_task(task_id: str, env_vars: dict) -> None:
    try:
        result = subprocess.run(
            ["/usr/bin/env", "python3", "/home/user/image/runner.py"],
            check=True,
            capture_output=True,
            text=True,
            timeout=3600,
            env=env_vars,
        )
        test_runs[task_id] = {
            "status": "completed",
            "output": result.stdout + (f"\n\nErrors:\n{result.stderr}" if result.stderr else ""),
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired as e:
        test_runs[task_id] = {
            "status": "failed",
            "error": f"Test timed out after {e.timeout} seconds",
            "output": e.stdout.decode() if e.stdout else "",
            "stderr": e.stderr.decode() if e.stderr else "",
        }
    except subprocess.CalledProcessError as e:
        test_runs[task_id] = {
            "status": "failed",
            "error": str(e),
            "output": e.stdout,
            "stderr": e.stderr,
        }
    except Exception as e:  # noqa: BLE001
        test_runs[task_id] = {
            "status": "failed",
            "error": str(e),
        }


def index(request: HttpRequest) -> HttpResponse:
    return render(request, "tests_interface/index.html")


def yocto_page(request: HttpRequest) -> HttpResponse:
    return render(request, "tests_interface/yocto.html")


def opensuse_page(request: HttpRequest) -> HttpResponse:
    return render(request, "tests_interface/opensuse.html")


def run_tests(request: HttpRequest) -> JsonResponse:
    referer = request.META.get("HTTP_REFERER", "")

    if "yocto" in referer:
        env_req = {"TESTED_DISTRO": "yocto"}
    elif "suse" in referer:
        env_req = {"TESTED_DISTRO": "suse"}
    else:
        env_req = {"TESTED_DISTRO": "all"}

    env_vars = os.environ.copy()
    env_vars.update(env_req)

    task_id = str(uuid.uuid4())
    test_runs[task_id] = {"status": "running"}

    thread = threading.Thread(target=_run_test_task, args=(task_id, env_vars))
    thread.daemon = True
    thread.start()

    return JsonResponse({"success": True, "task_id": task_id, "status": "running"})


def get_test_status(request: HttpRequest, task_id: str) -> JsonResponse:  # noqa: ARG001
    if task_id not in test_runs:
        return JsonResponse({"error": "Task not found"}, status=404)

    task_data = test_runs[task_id]
    return JsonResponse(
        {
            "task_id": task_id,
            "status": task_data.get("status"),
            "output": task_data.get("output", ""),
            "exit_code": task_data.get("exit_code"),
            "error": task_data.get("error"),
            "stderr": task_data.get("stderr", ""),
        },
    )
