from typing import Any

from django.apps import AppConfig
from django.core.management import call_command
from django.db.models.signals import post_migrate


def initialize_distros(sender: AppConfig, **kwargs: Any):  # noqa: ARG001
    call_command("init_distros")


class TestsInterfaceConfig(AppConfig):
    name = "tests_interface"

    def ready(self):
        post_migrate.connect(initialize_distros, sender=self)
