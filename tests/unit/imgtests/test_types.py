import pytest

from imgtests.types import Version


@pytest.mark.parametrize(
    ("raw_version", "version_str"),
    [
        ("10.0.0.0", "10"),
        ("09.08.07.06", "9.8.7.6"),
        ("BCA06", "BCA06"),
        ("6.14.0-33-generic", "6.14.0.33.generic"),
    ],
)
def test_version(raw_version: str, version_str: str) -> None:
    version = Version(raw_version)

    assert str(version) == version.version == version_str


@pytest.mark.parametrize(
    ("version1", "version2", "base"),
    [
        ("10.0.0.0", "9.0", 10),
        ("5.7.35", "5.7.0.35", 10),
        ("5.7.35", "5.7.5", 10),
        ("7.35", "", 10),
        ("BCA06", "BCA05", 16),
    ],
)
def test_version_comparison(version1: str, version2: str, base: int) -> None:
    assert Version(version1, base) > Version(version2, base)
