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

### Translations

Internationalization is implemented using [Django i18n](https://docs.djangoproject.com/en/6.0/topics/i18n/translation/).

The project supports two languages: English and Russian.

Translation files are located at `src/imgtests/web/locale/`. The `.po` files contain the actual translations, and `.mo` files (compiled binaries) are generated during the Docker build.

#### Marking strings for translation

In Django templates, wrap translatable strings with `{% translate %}` for simple strings and `{% blocktranslate %}` for strings with variables:

```
{% load i18n %}

{% translate "Test Dashboard" %}

{% blocktranslate %}Size: {{ report.size|filesizeformat }}{% endblocktranslate %}
```

#### Updating `.po` files after source changes

After adding or modifying `{% translate %}` tags, regenerate the `.po` files:

```bash
cd src/imgtests/web
django-admin makemessages -l ru
django-admin makemessages -d djangojs -l ru
```

Then edit the `.po` file and fill in the `msgstr` fields.

#### Adding a new language

1. Add the language code to the `LANGUAGES` list in `settings.py` (`src/imgtests/web/tests/settings.py`).
2. Generate a `.po` file:
   ```bash
   cd src/imgtests/web
   django-admin makemessages -l <language_code>
   ```
3. Translate the strings in the created `.po` file.

#### Compiling `.po` to `.mo`

During Docker build, `.mo` files are compiled using `msgfmt`. The `.mo` files are **not** stored in git - they are generated while building Docker image.

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
