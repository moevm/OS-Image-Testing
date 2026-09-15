from typing import Any

from django.core.management.base import BaseCommand
from tests_interface.models import Distribution

from imgtests.database.database import ImgtestsDatabase

DEFAULT_DISTROS: list[dict[str, str | int]] = [
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

DEFAULT_CONNECTIONS: list[dict[str, str | int | bool]] = [
    {
        "name": "yocto",
        "host": "10.5.0.10",
        "user": "root",
        "password": "",
        "port": 2222,
    },
    {
        "name": "opensuse",
        "host": "10.5.0.13",
        "user": "suser",
        "password": "password",
        "port": 1616,
    },
]


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        Distribution.objects.all().delete()

        created = 0
        for distro_data in DEFAULT_DISTROS:
            Distribution.objects.create(**distro_data)
            created += 1
            self.stdout.write(f"Created: {distro_data['display_name']}")

        database = ImgtestsDatabase()
        for connection_data in DEFAULT_CONNECTIONS:
            name = str(connection_data["name"])
            if database.get_connection(name) is not None:
                self.stdout.write(f"Connection for '{name}' already exists, keeping it.")
                continue
            database.upsert_connection(**connection_data)
            self.stdout.write(f"Created connection for: {name}")
        database.session.close_all()

        self.stdout.write(
            self.style.SUCCESS(f"Successfully initialized {created} default distributions"),
        )
