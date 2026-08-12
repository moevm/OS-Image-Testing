from django.urls import path, re_path
from django.views.i18n import JavaScriptCatalog

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("run-tests/", views.run_tests, name="run_tests"),
    path("test-status/<str:task_id>/", views.get_test_status, name="test_status"),
    path("reports/", views.report_list, name="report_list"),
    re_path(
        r"^reports/view/(?P<report_dir>.+)/(?P<filename>[^/]+\.html)$",
        views.view_report,
        name="view_report",
    ),
    re_path(
        r"^reports/static/(?P<report_dir>[^/]+)/(?P<file_path>.+)$",
        views.report_static_files,
        name="report_static",
    ),
    path("api/distros/", views.api_get_distros, name="api_get_distros"),
    path("api/distros/add/", views.api_add_distro, name="api_add_distro"),
    path("api/distros/remove/<int:distro_id>/", views.api_remove_distro, name="api_remove_distro"),
    path("api/distros/reset/", views.api_reset_distros, name="api_reset_distros"),
    path(
        "api/get_available_suites/",
        views.api_get_available_suites,
        name="api_get_available_suites",
    ),
    path(
        "api/get_suite_tests/<str:suite_name>/",
        views.api_get_suite_tests,
        name="api_get_suite_tests",
    ),
    path(
        "api/save_test_config/<str:distro_name>/",
        views.api_save_test_config,
        name="api_save_test_config",
    ),
    path(
        "api/get_test_config/<str:distro_name>/",
        views.api_get_test_config,
        name="api_get_test_config",
    ),
    path(
        "api/reset_test_config/<str:distro_name>/",
        views.api_reset_test_config,
        name="api_reset_test_config",
    ),
    path("<int:distro_id>/", views.distro_page, name="distro_page"),
    path("excel-reports/", views.excel_report_list, name="excel_report_list"),
    path(
        "excel-reports/<str:filename>/",
        views.download_excel_report,
        name="download_excel_report",
    ),
    path("api/export-excel/", views.api_export_excel, name="api_export_excel"),
    path(
        "api/experiments/",
        views.api_list_experiments,
        name="api_list_experiments",
    ),
    path(
        "api/generate-compare-report/",
        views.api_generate_compare_report,
        name="api_generate_compare_report",
    ),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
]
