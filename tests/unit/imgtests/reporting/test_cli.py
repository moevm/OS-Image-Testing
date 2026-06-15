import argparse

import pytest

from imgtests.constant import DISTRIBUTION_DESCRIPTIONS
from imgtests.reporting.cli import _parse_configuration_id_override


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
            "Whitespace around equals sign and values.",
            "Whitespace around equals sign and values.",
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
