# Вклад в проект

[English](../../CONTRIBUTING.md) | **Русский** |

Прежде всего, благодарим вас за желание внести вклад в этот проект.

## Среда разработки

Для работы с проектом необходимо установить следующие инструменты:

- **Python 3.11 или выше**: Требуется для зависимостей проекта и скриптов (используется модуль tomllib, доступный начиная с Python 3.11)
- **Docker**: Требуется для сборки и запуска контейнеров
- **Docker Compose**: Требуется для сборки и запуска контейнеров
- **make**: Требуется для запуска целей Makefile
- **uv**: Менеджер пакетов и проектов для Python

### Установка на Ubuntu

Установка `make` и `uv`:

```
sudo apt update
sudo apt install make
sudo apt install python3-pip
pip install uv
```

### Переводы

Интернационализация реализована с помощью [Django i18n](https://docs.djangoproject.com/en/6.0/topics/i18n/translation/).

Проект поддерживает два языка: английский и русский.

Файлы переводов находятся в `src/imgtests/web/locale/`. Файлы `.po` содержат переводы, а файлы `.mo` компилируются при сборке Docker.

#### Разметка строк для перевода

В шаблонах оборачивайте переводимые строки в `{% translate %}` для простых строк и в `{% blocktranslate %}` для строк с переменными:

```
{% load i18n %}

{% translate "Test Dashboard" %}

{% blocktranslate %}Size: {{ report.size|filesizeformat }}{% endblocktranslate %}
```

#### Обновление `.po` файлов после изменений в исходниках

После добавления или изменения тегов `{% translate %}`, перегенерируйте `.po` файлы:

```bash
cd src/imgtests/web
django-admin makemessages -l ru
```

Затем отредактируйте `.po` файл и заполните поля `msgstr`.

#### Добавление нового языка

1. Добавьте код языка в список `LANGUAGES` в `settings.py` (`src/imgtests/web/tests/settings.py`).
2. Сгенерируйте `.po` файл:
   ```bash
   cd src/imgtests/web
   django-admin makemessages -l <код_языка>
   ```
3. Переведите строки в созданном `.po` файле.

#### Компиляция `.po` в `.mo`

При сборке образа Docker файлы `.mo` компилируются с помощью `msgfmt`. Файлы `.mo` **не** хранятся в git.

### Запуск предварительных проверок и юнит-тестов

Проверить все файлы репозитория с помощью предварительных проверок (pre-commit hooks), описанных в файле [.pre-commit-config.yaml](../../.pre-commit-config.yaml):

```
make pre-commit-check
```

Запустить все юнит-тесты в директориях [tests/unit](../../tests/unit) и [tests/misc](../../tests/misc):

```
make unit-test
```

Конфигурация юнит-тестов описана в файле [pyproject.toml](../../pyproject.toml). Файлы и функции начинаются с префикса `test_`.
