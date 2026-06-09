import sys

from .web import run_django


def main() -> None:
    django_commands = [
        "runserver",
        "migrate",
        "db_worker",
        "makemigrations",
        "init_distros",
    ]
    if len(sys.argv) > 1 and sys.argv[1] in django_commands:
        sys.argv[0] = "manage.py"
        run_django()
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
