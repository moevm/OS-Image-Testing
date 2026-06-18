from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from imgtests.constant import DISTRIBUTION_DESCRIPTIONS
from imgtests.reporting.cli import (
    DATABASE_COMMAND,
    DISTRO_COMPARISON_COMMAND,
    DISTRO_COMPARISON_STATUS_COMMAND,
    EXPORT_TABLES,
    _parse_configuration_id_override,
    parse_args,
)


class TestParseConfigurationIdOverride:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("poky=10", ("poky", 10)),
            ("suse=20", ("suse", 20)),
            ("POKY=100", ("poky", 100)),
            ("SUSE=200", ("suse", 200)),
            ("poky = 10 ", ("poky", 10)),
            ("suse = 20 ", ("suse", 20)),
        ],
        ids=[
            "Valid poky configuration id.",
            "Valid suse configuration id.",
            "Uppercase distribution name (poky).",
            "Uppercase distribution name (suse).",
            "Whitespace around equals sign and values (poky).",
            "Whitespace around equals sign and values (suse).",
        ],
    )
    def test_valid_inputs(self, value: str, expected: tuple[str, int]) -> None:
        assert _parse_configuration_id_override(value) == expected

    def test_invalid_format_missing_equals(self) -> None:
        value = "poky10"
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            _parse_configuration_id_override(value)
        assert "Expected configuration id in DISTRO=ID format" in str(exc_info.value)

    def test_invalid_format_empty_distribution(self) -> None:
        value = "=10"
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            _parse_configuration_id_override(value)
        assert "Unsupported distribution ''." in str(exc_info.value)

    def test_invalid_distribution_name(self) -> None:
        value = "ubuntu=10"
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            _parse_configuration_id_override(value)
        assert "Unsupported distribution" in str(exc_info.value)
        valid_names = ", ".join(DISTRIBUTION_DESCRIPTIONS)
        assert valid_names in str(exc_info.value)

    def test_invalid_configuration_id_non_integer(self) -> None:
        value = "poky=abc"
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            _parse_configuration_id_override(value)
        assert "Configuration id for 'poky' must be an integer" in str(exc_info.value)

    def test_invalid_configuration_id_zero(self) -> None:
        value = "poky=0"
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            _parse_configuration_id_override(value)
        assert "Configuration id for 'poky' must be positive" in str(exc_info.value)

    def test_invalid_configuration_id_negative(self) -> None:
        value = "poky=-5"
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            _parse_configuration_id_override(value)
        assert "Configuration id for 'poky' must be positive" in str(exc_info.value)


class TestParseArgs:
    def test_database_command_with_required_args(self) -> None:
        argv = [
            DATABASE_COMMAND,
            "output.xlsx",
            "--db-url",
            "sqlite:///test.db",
            "--configuration-id",
            "poky=1",
            "--configuration-id",
            "suse=2",
        ]
        args = parse_args(argv)

        assert args.command == DATABASE_COMMAND
        assert args.output == Path("output.xlsx")
        assert args.db_url == "sqlite:///test.db"
        assert args.tables == list(EXPORT_TABLES)
        assert args.configuration_ids == [("poky", 1), ("suse", 2)]

    def test_database_command_with_custom_tables(self) -> None:
        argv = [
            DATABASE_COMMAND,
            "output.xlsx",
            "--db-url",
            "sqlite:///test.db",
            "--tables",
            "experiment",
            "--configuration-id",
            "poky=5",
        ]
        args = parse_args(argv)

        assert args.command == DATABASE_COMMAND
        assert args.output == Path("output.xlsx")
        assert args.db_url == "sqlite:///test.db"
        assert args.tables == ["experiment"]
        assert args.configuration_ids == [("poky", 5)]

    def test_database_command_with_single_configuration_id(self) -> None:
        argv = [
            DATABASE_COMMAND,
            "output.xlsx",
            "--db-url",
            "sqlite:///test.db",
            "--configuration-id",
            "suse=10",
        ]
        args = parse_args(argv)

        assert args.command == DATABASE_COMMAND
        assert args.output == Path("output.xlsx")
        assert args.db_url == "sqlite:///test.db"
        assert args.tables == list(EXPORT_TABLES)
        assert args.configuration_ids == [("suse", 10)]

    def test_distro_comparison_command_with_required_args(self) -> None:
        argv = [
            DISTRO_COMPARISON_COMMAND,
            "report.xlsx",
            "--experiment-ids",
            "10",
            "20",
        ]
        args = parse_args(argv)

        assert args.command == DISTRO_COMPARISON_COMMAND
        assert args.input == Path("report.xlsx")
        assert args.experiment_ids == ["10", "20"]
        assert args.output is None

    def test_distro_comparison_command_with_output(self) -> None:
        argv = [
            DISTRO_COMPARISON_COMMAND,
            "report.xlsx",
            "--output",
            "comparison.xlsx",
            "--experiment-ids",
            "100",
        ]
        args = parse_args(argv)

        assert args.command == DISTRO_COMPARISON_COMMAND
        assert args.input == Path("report.xlsx")
        assert args.output == Path("comparison.xlsx")
        assert args.experiment_ids == ["100"]

    def test_missing_required_command_raises_error(self) -> None:
        argv = ["--db-url", "sqlite:///test.db"]

        with pytest.raises(SystemExit) as exc_info:
            parse_args(argv)

        assert exc_info.value.code != 0

    def test_database_command_missing_output_raises_error(self) -> None:
        argv = [
            DATABASE_COMMAND,
            "--db-url",
            "sqlite:///test.db",
            "--configuration-id",
            "poky=1",
            "--configuration-id",
            "suse=2",
        ]

        with pytest.raises(SystemExit) as exc_info:
            parse_args(argv)

        assert exc_info.value.code != 0

    def test_database_command_missing_db_url_raises_error(self) -> None:
        argv = [
            DATABASE_COMMAND,
            "output.xlsx",
            "--configuration-id",
            "poky=1",
            "--configuration-id",
            "suse=2",
        ]

        with pytest.raises(SystemExit) as exc_info:
            parse_args(argv)

        assert exc_info.value.code != 0

    def test_database_command_missing_configuration_id_raises_error(self) -> None:
        argv = [
            DATABASE_COMMAND,
            "output.xlsx",
            "--db-url",
            "sqlite:///test.db",
        ]

        with pytest.raises(SystemExit) as exc_info:
            parse_args(argv)

        assert exc_info.value.code != 0

    def test_database_command_with_absolute_path(self) -> None:
        argv = [
            DATABASE_COMMAND,
            "/var/lib/output.xlsx",
            "--db-url",
            "sqlite:///test.db",
            "--configuration-id",
            "poky=1",
            "--configuration-id",
            "suse=2",
        ]
        args = parse_args(argv)

        assert args.output == Path("/var/lib/output.xlsx")
        assert args.db_url == "sqlite:///test.db"
        assert args.configuration_ids == [("poky", 1), ("suse", 2)]
        assert args.tables == list(EXPORT_TABLES)

    def test_database_command_with_relative_path(self) -> None:
        argv = [
            DATABASE_COMMAND,
            "./output.xlsx",
            "--db-url",
            "sqlite:///test.db",
            "--configuration-id",
            "poky=125",
            "--configuration-id",
            "suse=225",
        ]
        args = parse_args(argv)

        assert args.output == Path("./output.xlsx")
        assert args.db_url == "sqlite:///test.db"
        assert args.configuration_ids == [("poky", 125), ("suse", 225)]
        assert args.tables == list(EXPORT_TABLES)

    def test_distro_comparison_command_single_experiment_id(self) -> None:
        argv = [
            DISTRO_COMPARISON_COMMAND,
            "report.xlsx",
            "--experiment-ids",
            "100",
        ]
        args = parse_args(argv)

        assert args.command == DISTRO_COMPARISON_COMMAND
        assert args.experiment_ids == ["100"]

    def test_comparison_status_command(self) -> None:
        argv = [
            DISTRO_COMPARISON_STATUS_COMMAND,
            "--epsilon-percent",
            "100",
        ]
        args = parse_args(argv)

        assert args.command == DISTRO_COMPARISON_STATUS_COMMAND
        assert args.epsilon_percent == 100  # noqa: PLR2004
