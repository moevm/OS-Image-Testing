import sys

from .web import run_django


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "runserver":
        sys.argv[0] = "manage.py"
        run_django()
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
