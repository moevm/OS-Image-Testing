import os
from typing import TYPE_CHECKING

from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.tasks import TaskResultStatus

from .tasks import run_test_task

if TYPE_CHECKING:
    from django.http.response import HttpResponse
    from django.tasks import TaskResult


test_runs = {}


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

    result: TaskResult = run_test_task.enqueue(env_vars)

    task_id = str(result.id)
    test_runs[task_id] = {
        "status": "running",
        "result": result,
        "task_id": task_id,
    }

    return JsonResponse({"success": True, "task_id": task_id, "status": "running"})


def get_test_status(request: HttpRequest, task_id: str) -> JsonResponse:  # noqa: ARG001
    if task_id not in test_runs:
        return JsonResponse({"error": "Task not found"}, status=404)

    task_data = test_runs[task_id]
    result = task_data["result"]

    result.refresh()

    if not result.is_finished:
        return JsonResponse(
            {
                "task_id": task_id,
                "status": "running",
                "output": "",
                "exit_code": None,
                "error": None,
                "stderr": "",
            },
        )

    if result.status == TaskResultStatus.SUCCESSFUL:
        task_result = result.return_value
        return JsonResponse(
            {
                "task_id": task_id,
                "status": task_result.get("status", "completed"),
                "output": task_result.get("output", ""),
                "exit_code": task_result.get("exit_code"),
                "error": task_result.get("error"),
                "stderr": task_result.get("stderr", ""),
            },
        )
    error_msg = "Task failed"
    if result.errors:
        error_msg = str(result.errors[-1])

    return JsonResponse(
        {
            "task_id": task_id,
            "status": "failed",
            "error": error_msg,
            "output": "",
            "stderr": "",
        },
    )
