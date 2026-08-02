# Agents Guide for OS-Image-Testing

## Technological stack

- **Python**: 3.14.4 (requires Python 3.11+ for the build system)
- **Build system**: GNU Make, uv (dependency manager)
- **Containerization**: Docker, Docker Compose
- **Testing framework**: pytest, pytest-cov
- **Code quality**: Ruff (linting and formatting)
- **Web framework**: Django
- **Database**: PostgreSQL

## Repository structure

| Folder    | Description                                  |
|-----------|----------------------------------------------|
| `conf/`   | Configuration files for Yocto and other      |
| `docker/` | Docker build files and Compose configuration |
| `docs/`   | Markdown documentation                       |
| `layers/` | Yocto layers                                 |
| `scripts/`| Shell scripts                                |
| `src/`    | Python library source code                   |
| `tests/`  | Unit tests and other tests                   |

## Library structure

The `src/imgtests/` directory contains the main Python library for OS image testing. It is organized into five high-level components:

1. **Test orchestration** (`runner.py`, `planning/`) - Builds and executes test plans and manages test runs
2. **Test execution**
   - **suites/** - Test suites organized by subsystem (system, drive, general, network, ipc, memory, syscalls and etc)
   - **exec/** - Test utilities and observers (loaders, observers, pkgmgrs, exec.py for SSH client)
3. **Data layer** (`database/`) - Database models and connection
4. **Types and constants** (`types.py`, `constant.py`) - Core types and constants
5. **Reporting** (`reporting/`) - Generates HTML and Excel reports, CLI output

## Code conventions

### Python

- **Docstring convention**: Google style
- Dynamic typing (`typing.Any`) allowed
- Missing docstrings allowed for internal functions
- Boolean positional arguments allowed

### Pre-commit hooks

The project uses pre-commit with the following hooks:
- Ruff (linting and formatting)
- ShellCheck (shell scripts)
- YAML/JSON validation
- Trailing whitespace, mixed line endings
- Private key detection
- Shebang and executable checks

```bash
make pre-commit-check
```

## Running unit tests

Run unit tests using Makefile

```bash
# Run all unit and misc tests with coverage
make unit-test
```

### Test discovery

Tests are discovered in:
- `tests/unit/` - Unit tests
- `tests/misc/` - Miscellaneous tests

## When to run tests and pre-commit hooks

**Always run unit tests and pre-commit hooks after making changes to the codebase.** Coverage reports help identify untested code paths.

### Trigger conditions:

- After modifying any code in `src/imgtests/`
- After adding new test utilities or fixtures in `tests/`
- After changing dependencies in `pyproject.toml`
