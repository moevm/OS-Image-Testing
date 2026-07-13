import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from django.core.management import call_command
from django.http import FileResponse, Http404, HttpRequest, JsonResponse
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.tasks import TaskResultStatus
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from pydantic_core._pydantic_core import ValidationError
from sqlalchemy import create_engine

from imgtests.constant import CONFIG_DIR, EXCEL_REPORTS_DIR, PROG_LOG_PATH, REPORTS_DIR
from imgtests.database.database import ImgtestsDatabase, PostgresCreds
from imgtests.reporting.excel_export import export_database_to_excel
from imgtests.reporting.html_report import ReportGenerator
from imgtests.runner import get_test_name
from imgtests.suites.map import ALL_SUITES

from .models import Distribution
from .tasks import run_test_task

if TYPE_CHECKING:
    from django.tasks import TaskResult


logger = logging.getLogger(__name__)
test_runs = {}


def api_get_available_suites(request: HttpRequest) -> JsonResponse:  # noqa: ARG001
    suites_info = {
        suite_name: {
            "description": suite.description,
            "default_duration": suite.total_duration,
            "test_count": len(suite.tests),
        }
        for suite_name, suite in ALL_SUITES.items()
    }

    return JsonResponse(suites_info)


def api_get_suite_tests(request: HttpRequest, suite_name: str) -> JsonResponse:  # noqa: ARG001
    if suite_name not in ALL_SUITES:
        return JsonResponse({"error": f"Suite {suite_name} not found"}, status=404)
    tests_list = [
        {"name": get_test_name(test), "type": "class"} for test in ALL_SUITES[suite_name].tests
    ]
    return JsonResponse(tests_list, safe=False)


@csrf_exempt
@require_http_methods(["POST"])
def api_save_test_config(request: HttpRequest, distro_name: str) -> JsonResponse:
    try:
        config = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not isinstance(config, dict):
        return JsonResponse({"error": "Invalid config format"}, status=400)

    try:
        CONFIG_DIR.mkdir(exist_ok=True, parents=True)
        config_file = CONFIG_DIR / f"{distro_name}_config.json"
        with Path.open(config_file, "w") as f:
            json.dump(config, f, indent=4)
    except Exception as e:  # noqa: BLE001
        return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"success": True, "config_file": str(config_file)})


def api_get_test_config(request: HttpRequest, distro_name: str) -> JsonResponse:  # noqa: ARG001
    config_file = CONFIG_DIR / f"{distro_name}_config.json"

    if config_file.exists():
        try:
            with Path.open(config_file, "r") as f:
                config = json.load(f)
        except Exception as e:  # noqa: BLE001
            return JsonResponse({"error": str(e)}, status=500)
        return JsonResponse(config)

    default_config = {
        "suites": ["FILE_SUITE", "MEMORY_SUITE", "SYSCALLS_SUITE", "IPC_SUITE", "NETWORK_SUITE"],
        "suite_durations": {
            "FILE_SUITE": ALL_SUITES["FILE_SUITE"].total_duration,
            "MEMORY_SUITE": ALL_SUITES["MEMORY_SUITE"].total_duration,
            "SYSCALLS_SUITE": ALL_SUITES["SYSCALLS_SUITE"].total_duration,
            "IPC_SUITE": ALL_SUITES["IPC_SUITE"].total_duration,
            "NETWORK_SUITE": ALL_SUITES["NETWORK_SUITE"].total_duration,
        },
        "selected_tests": {},
        "test_runs_count": 1,
    }

    return JsonResponse(default_config)


@csrf_exempt
@require_http_methods(["POST"])
def api_reset_test_config(request: HttpRequest, distro_name: str) -> JsonResponse:  # noqa: ARG001
    config_file = CONFIG_DIR / f"{distro_name}_config.json"

    if config_file.exists():
        config_file.unlink()

    return JsonResponse({"success": True})


def index(request: HttpRequest) -> HttpResponse:
    distributions = Distribution.objects.filter(is_active=True)
    return render(request, "tests_interface/index.html", {"distributions": distributions})


def distro_page(request: HttpRequest, distro_id: int) -> HttpResponse:
    distro = get_object_or_404(Distribution, id=distro_id, is_active=True)
    return render(request, "tests_interface/distro_page.html", {"distro": distro})


def report_list(request: HttpRequest) -> HttpResponse:
    reports: list[dict[str, str | float]] = []
    if not REPORTS_DIR.exists():
        return render(request, "tests_interface/reports_list.html", {"reports": reports})
    for report_dir in sorted(REPORTS_DIR.iterdir(), reverse=True):
        reports.extend(__find_reports(report_dir))
    profiled_dir = REPORTS_DIR / "profiled"
    if not profiled_dir.exists():
        return render(request, "tests_interface/reports_list.html", {"reports": reports})
    for report_dir in sorted(profiled_dir.iterdir(), reverse=True):
        reports.extend(__find_reports(report_dir))

    return render(request, "tests_interface/reports_list.html", {"reports": reports})


def view_report(request: HttpRequest, report_dir: str, filename: str) -> HttpResponse:  # noqa: ARG001
    report_path = __safe_relative_path(report_dir, filename)
    report_file = REPORTS_DIR / report_path

    if not report_file.exists() or not report_file.is_file():
        e = f"Report not found: {report_dir}/{filename}"
        raise Http404(e)

    try:
        with Path.open(report_file, "r", encoding="utf-8") as f:
            content_str = f.read()

        content_str = content_str.replace(
            'src="plots/',
            f'src="/reports/static/{report_path.parent.as_posix()}/plots/',
        )

        content_bytes = content_str.encode("utf-8")
        return HttpResponse(content_bytes, content_type="text/html")
    except Exception as e:
        error_message = f"Error reading report: {e}"
        raise Http404(error_message) from e


def report_static_files(request: HttpRequest, report_dir: str, file_path: str) -> HttpResponse:  # noqa: ARG001
    static_path = __safe_relative_path(report_dir, file_path)
    static_file = REPORTS_DIR / static_path

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
        distro = get_object_or_404(Distribution, id=distro_id, is_active=True)
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError, AttributeError:
            body = {}
        test_runs_count = body.get("test_runs_count", 1)
    else:
        return JsonResponse({"error": "Invalid referer"}, status=400)

    try:
        runner = body.get("runner", "default")
    except AttributeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    result: TaskResult = run_test_task.enqueue(
        distro=distro.name,
        mode=runner,
        test_runs_count=test_runs_count,
        config=body.get("config") if runner == "profiled" else None,
    )

    task_id = str(result.id)
    test_runs[task_id] = {
        "status": "running",
        "result": result,
        "task_id": task_id,
    }

    return JsonResponse({"success": True, "task_id": task_id, "status": "running"})


def get_run_progress(request: HttpRequest) -> JsonResponse:  # noqa: ARG001
    progress_file = Path(PROG_LOG_PATH)
    if progress_file.exists():
        try:
            with Path.open(PROG_LOG_PATH, encoding="utf-8") as file:
                data = json.load(file)
            return JsonResponse(data)
        except json.decoder.JSONDecodeError:
            return JsonResponse({})
    return JsonResponse({})


def flush_progress_handle(request: HttpRequest) -> JsonResponse:  # noqa: ARG001
    for handle in logging.getLogger().handlers:
        if handle.name == "progress_handler":
            handle.flush()
            return JsonResponse({"status": "success"})
    return JsonResponse({"status": "failure"})


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
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    name = data.get("name", "").strip()
    display_name = data.get("display_name", "").strip()
    description = data.get("description", "").strip()

    if Distribution.objects.filter(name=name).exists():
        return JsonResponse(
            {"error": "Distribution with this name already exists"},
            status=400,
        )

    distro = Distribution.objects.create(
        name=name,
        display_name=display_name,
        description=description or f"Run tests for {display_name} platform",
    )

    return JsonResponse(
        {
            "success": True,
            "distro": {
                "id": distro.id,
                "name": distro.name,
                "display_name": distro.display_name,
                "description": distro.description,
            },
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
def api_remove_distro(request: HttpRequest, distro_id: int) -> JsonResponse:  # noqa: ARG001
    deleted, _ = Distribution.objects.filter(id=distro_id).delete()
    if deleted:
        return JsonResponse({"success": True})
    return JsonResponse({"error": "Distribution not found"}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def api_reset_distros(request: HttpRequest) -> JsonResponse:  # noqa: ARG001
    try:
        call_command("init_distros")
        return JsonResponse({"success": True})
    except Exception as e:  # noqa: BLE001
        return JsonResponse({"error": f"Failed to reset: {e}"}, status=500)


def api_get_distros(request: HttpRequest) -> JsonResponse:  # noqa: ARG001
    distributions = list(
        Distribution.objects.filter(is_active=True).values(
            "id",
            "name",
            "display_name",
            "description",
        ),
    )
    return JsonResponse({"distributions": distributions})


def __find_reports(reports_path: Path) -> list[dict[str, str | float]]:
    if not reports_path.is_dir():
        return []
    html_files = list(reports_path.glob("*.html"))
    report_dir = reports_path.relative_to(REPORTS_DIR).as_posix()
    return [
        {
            "name": f"{report_dir} / {html_file.name}",
            "report_dir": report_dir,
            "filename": html_file.name,
            "created": html_file.stat().st_mtime,
            "size": html_file.stat().st_size,
            "dir_name": report_dir,
            "file_name": html_file.name,
        }
        for html_file in html_files
    ]


def __safe_relative_path(*parts: str) -> Path:
    relative_path = Path(*parts)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        e = "Invalid report path"
        raise Http404(e)
    return relative_path


@csrf_exempt
@require_http_methods(["POST"])
def api_export_excel(request: HttpRequest) -> JsonResponse:  # noqa: ARG001
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    output_path = EXCEL_REPORTS_DIR / f"export_{timestamp}.xlsx"
    try:
        db_creds = PostgresCreds()
    except ValidationError:
        logger.exception("Failed to get database credentials from environment.")
        return JsonResponse({"error": "Export failed."}, status=500)

    db_url = (
        f"postgresql+psycopg://{db_creds.user}:{db_creds.password}@"
        f"{db_creds.host}:{db_creds.port}/{db_creds.database_name}"
    )

    try:
        engine = create_engine(db_url)
        export_database_to_excel(
            engine=engine,
            output_path=output_path,
            configuration_ids={"poky": 1, "suse": 2},
        )
    except Exception as err:  # noqa: BLE001
        return JsonResponse({"error": f"Export failed: {err}"}, status=500)

    logger.info("Report '%s' successfully created.", str(output_path))
    return JsonResponse(
        {
            "success": True,
            "file_url": f"excel_reports/{output_path.name}",
            "filename": output_path.name,
            "created": timestamp,
        },
    )


def excel_report_list(request: HttpRequest) -> HttpResponse:
    reports: list[dict[str, str | float]] = []
    if not EXCEL_REPORTS_DIR.exists():
        return render(request, "tests_interface/excel_reports.html", {"reports": reports})

    for file_path in sorted(EXCEL_REPORTS_DIR.glob("*.xlsx"), reverse=True):
        stat = file_path.stat()
        reports.append(
            {
                "name": file_path.name,
                "size": stat.st_size,
                "created": stat.st_mtime,
            },
        )

    return render(request, "tests_interface/excel_reports.html", {"reports": reports})


def download_excel_report(request: HttpRequest, filename: str) -> FileResponse:  # noqa: ARG001
    file_path = EXCEL_REPORTS_DIR / filename

    if not file_path.exists():
        e = "File not found"
        raise Http404(e)

    return FileResponse(
        Path.open(file_path, "rb"),
        filename=filename,
        as_attachment=True,
    )


def api_list_experiments(request: HttpRequest) -> JsonResponse:  # noqa: ARG001
    try:
        experiments = ImgtestsDatabase().list_experiments()
    except Exception as e:  # noqa: BLE001
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(
        {
            "experiments": [
                {
                    "id": exp.experiment_id,
                    "description": exp.description,
                    "os": exp.configuration.os if exp.configuration else "unknown",
                    "started_at": (exp.started_at.isoformat() if exp.started_at else None),
                    "ended_at": exp.ended_at.isoformat() if exp.ended_at else None,
                    "tests_total": exp.tests_total,
                    "tests_passed": exp.tests_passed,
                    "tests_failed": exp.tests_failed,
                    "tests_broken": exp.tests_broken,
                    "tests_skipped": exp.tests_skipped,
                }
                for exp in experiments
            ],
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
def api_generate_compare_report(request: HttpRequest) -> JsonResponse:
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid request body"}, status=400)

    try:
        exp_id_1 = int(body.get("experiment_id_1"))
        exp_id_2 = int(body.get("experiment_id_2"))
    except TypeError, ValueError:
        return JsonResponse({"error": "Invalid experiment id type"}, status=400)

    try:
        report_gen = ReportGenerator(ImgtestsDatabase())
        report_path = report_gen.generate_compare_html_report(
            sorted([exp_id_1, exp_id_2]),
            out_dir=REPORTS_DIR,
        )
    except Exception as e:  # noqa: BLE001
        return JsonResponse({"error": str(e)}, status=500)

    if report_path is None:
        return JsonResponse({"error": "Failed to generate report"}, status=500)
    return JsonResponse(
        {
            "success": True,
            "report_url": str(report_path.relative_to(REPORTS_DIR)),
        },
    )
