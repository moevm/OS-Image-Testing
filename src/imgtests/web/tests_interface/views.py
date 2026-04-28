import os
from pathlib import Path
from typing import TYPE_CHECKING

from django.http import Http404, HttpRequest, JsonResponse
from django.http.response import HttpResponse
from django.shortcuts import render
from django.tasks import TaskResultStatus

from .tasks import run_test_task

if TYPE_CHECKING:
    from django.tasks import TaskResult


test_runs = {}


def index(request: HttpRequest) -> HttpResponse:
    return render(request, "tests_interface/index.html")


def yocto_page(request: HttpRequest) -> HttpResponse:
    return render(request, "tests_interface/yocto.html")


def opensuse_page(request: HttpRequest) -> HttpResponse:
    return render(request, "tests_interface/opensuse.html")


def report_list(request: HttpRequest) -> HttpResponse:
    reports_dir = Path("/home/user/results/profiled")
    reports = []
    if reports_dir.exists():
        for report_dir in sorted(reports_dir.iterdir(), reverse=True):
            if report_dir.is_dir():
                html_files = list(report_dir.glob("*.html"))
                for html_file in html_files:
                    created_time = html_file.stat().st_mtime

                    reports.append(
                        {
                            "name": f"{report_dir.name} / {html_file.name}",
                            "report_dir": report_dir.name,
                            "filename": html_file.name,
                            "created": created_time,
                            "size": html_file.stat().st_size,
                            "dir_name": report_dir.name,
                            "file_name": html_file.name,
                        }
                    )

    return render(request, "tests_interface/reports_list.html", {"reports": reports})


def view_report(request: HttpRequest, report_dir: str, filename: str) -> HttpResponse:  # noqa: ARG001
    reports_base_dir = Path("/home/user/results/profiled")
    report_file = reports_base_dir / report_dir / filename

    if not report_file.exists() or not report_file.is_file():
        ret = f"Report not found: {report_dir}/{filename}"
        raise Http404(ret)

    try:
        with Path.open(report_file, "r", encoding="utf-8") as f:
            content_str = f.read()

        content_str = content_str.replace(
            'src="plots/',
            f'src="/reports/static/{report_dir}/plots/',
        )

        content_bytes = content_str.encode("utf-8")
        return HttpResponse(content_bytes, content_type="text/html")
    except Exception as e:
        error_message = f"Error reading report: {e}"
        raise Http404(error_message) from e


def report_static_files(request: HttpRequest, report_dir: str, file_path: str) -> HttpResponse:  # noqa: ARG001
    reports_base_dir = Path("/home/user/results/profiled")
    static_file = reports_base_dir / report_dir / file_path

    if not static_file.exists() or not static_file.is_file():
        ret = f"Static file not found: {report_dir}/{file_path}"
        raise Http404(ret)

    content_type = "application/octet-stream"
    if file_path.endswith(".png"):
        content_type = "image/png"
    elif file_path.endswith(".jpg") or file_path.endswith(".jpeg"):  # noqa: PIE810
        content_type = "image/jpeg"
    elif file_path.endswith(".svg"):
        content_type = "image/svg+xml"
    elif file_path.endswith(".gif"):
        content_type = "image/gif"
    elif file_path.endswith(".css"):
        content_type = "text/css"
    elif file_path.endswith(".js"):
        content_type = "application/javascript"

    try:
        with Path.open(static_file, "rb") as f:
            content = f.read()
        return HttpResponse(content, content_type=content_type)
    except Exception as e:
        error_message = f"Error reading static file: {e}"
        raise Http404(error_message) from e


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
