import os
from pathlib import Path
from typing import TypeVar

import pytest

from imgtests.environment import env_var_to_type

T = TypeVar("T", bound=int | float | Path | str)


class TestEnvVarToType:
    def test_env_var_to_type_not_supported(self) -> None:
        variable = "VAR1"
        os.environ[variable] = ""
        with pytest.raises(ValueError, match=f"Unsupported val_type='{complex}' provided."):
            env_var_to_type(variable, complex)
        del os.environ[variable]

    def test_env_var_to_type_not_found(self) -> None:
        variable = "NONEXISTENT_VAR"
        with pytest.raises(ValueError, match=f"Environment variable '{variable}' not found."):
            env_var_to_type(variable, str)

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("true", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("0", False),
            ("no", False),
            ("off", False),
        ],
    )
    def test_env_var_to_bool(self, value: str, expected: bool) -> None:
        variable = "BOOL_ENV"
        os.environ[variable] = value
        assert env_var_to_type("BOOL_ENV", bool) == expected
        del os.environ[variable]

    @pytest.mark.parametrize(
        ("value", "type_", "expected"),
        [
            ("123", int, 123),
            ("12.58", float, 12.58),
            ("hello", str, "hello"),
            ("/home/foobar", Path, Path("/home/foobar")),
        ],
    )
    def test_env_var_to_another_type(self, value: str, type_: type[T], expected: T) -> None:
        variable = "VAR1"
        os.environ[variable] = value
        assert env_var_to_type(variable, type_) == expected
        del os.environ[variable]

    @pytest.mark.parametrize(
        ("value", "type_", "default"),
        [
            ("123", int, 123),
            ("12.58", float, 12.58),
            ("hello", str, "hello"),
            ("/home/foobar", Path, Path("/home/foobar")),
        ],
    )
    def test_env_var_to_type_check_default(self, value: str, type_: type[T], default: T) -> None:
        assert env_var_to_type(value, type_, default) == default
