from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("yocto/", views.yocto_page, name="yocto"),
    path("opensuse/", views.opensuse_page, name="opensuse"),
    path("run-tests/", views.run_tests, name="run_tests"),
    path("test-status/<str:task_id>/", views.get_test_status, name="test_status"),
]
