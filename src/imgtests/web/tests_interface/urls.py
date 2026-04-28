from django.urls import path, re_path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("run-tests/", views.run_tests, name="run_tests"),
    path("test-status/<str:task_id>/", views.get_test_status, name="test_status"),
    path("reports/", views.report_list, name="report_list"),
    re_path(
        r"^reports/view/(?P<report_dir>[^/]+)/(?P<filename>.+\.html)$",
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
    path("api/distros/remove/<str:distro_id>/", views.api_remove_distro, name="api_remove_distro"),
    path("api/distros/reset/", views.api_reset_distros, name="api_reset_distros"),
    path("<str:distro_id>/", views.distro_page, name="distro_page"),
]
