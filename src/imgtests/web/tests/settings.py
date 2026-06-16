import logging
from pathlib import Path
from typing import Final

from django.core.management.utils import get_random_secret_key
from pydantic import Field
from pydantic_settings import BaseSettings

from imgtests.constant import LOG_PATH
from imgtests.logger import LogLevel, set_handlers


class DjangoSettings(BaseSettings):
    log_level: LogLevel = Field(default="info", validation_alias="LOG_LEVEL")
    db_name: str = Field(validation_alias="POSTGRES_DB")
    db_user: str = Field(validation_alias="POSTGRES_USER")
    db_password: str = Field(validation_alias="POSTGRES_PASSWORD")
    db_host: str = Field(validation_alias="POSTGRES_HOST")
    db_port: int = Field(validation_alias="POSTGRES_PORT", ge=0, le=65535)


ENV_SETTINGS: Final = DjangoSettings()
LOG_PATH.parent.mkdir(exist_ok=True)
set_handlers(logging.getLogger(), Path(LOG_PATH), log_level=ENV_SETTINGS.log_level)

BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = get_random_secret_key()
DEBUG = True
ALLOWED_HOSTS = []
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_tasks",
    "django_tasks_db",
    "tests_interface",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "tests.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "tests.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": ENV_SETTINGS.db_name,
        "USER": ENV_SETTINGS.db_user,
        "PASSWORD": ENV_SETTINGS.db_password,
        "HOST": ENV_SETTINGS.db_host,
        "PORT": ENV_SETTINGS.db_port,
    },
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "ru"

LANGUAGES = [
    ("en", "English"),
    ("ru", "Русский"),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

TASKS = {
    "default": {
        "BACKEND": "django_tasks_db.DatabaseBackend",
        "OPTIONS": {
            "queue_name": "default",
            "max_attempts": 1,
            "expires_after": 3600,
        },
    },
}
