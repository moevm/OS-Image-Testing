# Contributing

**English** | [Русский](docs/i18n/CONTRIBUTING_ru.md) |

First of all, thank you for your desire to contribute in that project.

## Development environment

You will need to install the following tools to work with the project:

- **Python 3.11 or higher**: Required for project dependencies and scripts (uses tomllib module available since Python 3.11)
- **Docker**: Required for building and running containers
- **Docker Compose**: Required for building and running containers
- **make**: Required to run Makefile targets
- **uv**: Package manager and project manager for Python

### Installation on Ubuntu

Installing `make` and `uv`:

```
sudo apt update
sudo apt install make
sudo apt install python3-pip
pip install uv
```

### Running pre-commit-checks and unit-tests

Checks all the repository files using pre-commit hooks described in the [.pre-commit-config.yaml](.pre-commit-config.yaml) file:

```
make pre-commit-check
```

Runs all unit tests in the [tests/unit](tests/unit) and [tests/misc](tests/misc) directories:

```
make unit-test
```

The unit test configuration is described within [pyproject.toml](pyproject.toml) file. The testing files and functions begin with the `test_` prefix.
