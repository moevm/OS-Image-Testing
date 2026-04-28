import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from django.http import Http404, HttpRequest, JsonResponse
from django.http.response import HttpResponse
from django.shortcuts import render
from django.tasks import TaskResultStatus
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .distros_config import (
    add_distribution,
    get_distribution_by_id,
    get_distributions,
    remove_distribution,
    reset_to_default,
)
from .tasks import run_test_task

if TYPE_CHECKING:
    from django.tasks import TaskResult


test_runs = {}


def index(request: HttpRequest) -> HttpResponse:
    distributions = get_distributions()
    return render(request, "tests_interface/index.html", {"distributions": distributions})


def distro_page(request: HttpRequest, distro_id: str) -> HttpResponse:
    distro = get_distribution_by_id(distro_id)
    if not distro:
        e = f"Distribution '{distro_id}' not found"
        raise Http404(e)

    return render(request, "tests_interface/distro_page.html", {"distro": distro})


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
                        },
                    )

    return render(request, "tests_interface/reports_list.html", {"reports": reports})


def view_report(request: HttpRequest, report_dir: str, filename: str) -> HttpResponse:  # noqa: ARG001
    reports_base_dir = Path("/home/user/results/profiled")
    report_file = reports_base_dir / report_dir / filename

    if not report_file.exists() or not report_file.is_file():
        e = f"Report not found: {report_dir}/{filename}"
        raise Http404(e)

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
        e = f"Static file not found: {report_dir}/{file_path}"
        raise Http404(e)

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

    match = re.search(r"/([^/]+)/$", referer)
    if match:
        distro_id = match.group(1)
        env_req = {"TESTED_DISTRO": distro_id}
    else:
        env_req = {"TESTED_DISTRO": "None"}

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


@csrf_exempt
@require_http_methods(["POST"])
def api_add_distro(request: HttpRequest) -> JsonResponse:
    try:
        data = json.loads(request.body)
        name = data.get("name", "").strip()
        display_name = data.get("display_name", "").strip()
        description = data.get("description", "").strip()

        if not name or not display_name:
            return JsonResponse({"error": "Name and display name are required"}, status=400)

        new_distro = add_distribution(name, display_name, description)

        if new_distro:
            return JsonResponse({"success": True, "distro": new_distro})
        return JsonResponse({"error": "Distribution already exists"}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def api_remove_distro(request: HttpRequest, distro_id: str) -> JsonResponse:  # noqa: ARG001
    default_ids = ["yocto", "opensuse"]
    if distro_id in default_ids:
        return JsonResponse({"error": "Cannot remove default distributions"}, status=400)

    if remove_distribution(distro_id):
        return JsonResponse({"success": True})
    return JsonResponse({"error": "Distribution not found"}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def api_reset_distros(request: HttpRequest) -> JsonResponse:  # noqa: ARG001
    if reset_to_default():
        return JsonResponse({"success": True})
    return JsonResponse({"error": "Failed to reset"}, status=500)


def api_get_distros(request: HttpRequest) -> JsonResponse:  # noqa: ARG001
    distributions = get_distributions()
    return JsonResponse({"distributions": distributions})
