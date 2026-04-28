from django.urls import path, re_path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("yocto/", views.yocto_page, name="yocto"),
    path("opensuse/", views.opensuse_page, name="opensuse"),
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
]
