import sys


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "runserver":
        from .web import run_django

        sys.argv[0] = "manage.py"
        run_django()
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
