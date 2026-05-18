from typing import Any

from django.core.management.base import BaseCommand
from tests_interface.models import Distribution

DEFAULT_DISTROS = [
    {
        "name": "yocto",
        "display_name": "Yocto Project",
        "description": "Run tests for Yocto platform",
        "order": 1,
    },
    {
        "name": "opensuse",
        "display_name": "OpenSUSE",
        "description": "Run tests for OpenSUSE platform",
        "order": 2,
    },
]


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any):  # noqa: ARG002
        Distribution.objects.all().delete()

        created = 0
        for distro_data in DEFAULT_DISTROS:
            Distribution.objects.create(**distro_data)
            created += 1
            self.stdout.write(f"Created: {distro_data['display_name']}")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully initialized {created} default distributions"),
        )
