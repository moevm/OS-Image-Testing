from __future__ import annotations

from textwrap import dedent

import pytest

from imgtests.exec.osinfo import _parse_os_release


@pytest.mark.parametrize(
    ("content", "result"),
    [
        (
            dedent(
                """
                # comment line
                ID="opensuse-leap"
                NAME="openSUSE Leap"
                VERSION_ID="15.5"
                PRETTY_NAME="openSUSE Leap 15.5"
                """
            ),
            {
                "ID": "opensuse-leap",
                "NAME": "openSUSE Leap",
                "VERSION_ID": "15.5",
                "PRETTY_NAME": "openSUSE Leap 15.5",
            },
        ),
        (
            dedent(
                """

                # first comment
                ID=ubuntu

                # indented comment
                NAME=Ubuntu

                """
            ),
            {
                "ID": "ubuntu",
                "NAME": "Ubuntu",
            },
        ),
        (
            dedent(
                """
                ID=arch
                THIS IS MALFORMED
                NAME=Arch Linux
                """
            ),
            {
                "ID": "arch",
                "NAME": "Arch Linux",
            },
        ),
    ],
    ids=[
        "parse basic fields.",
        "ignores comments and blank lines.",
        "ignores lines without equal",
    ],
)
def test__parse_os_release(content: str, result: dict[str, str]) -> None:
    data = _parse_os_release(content)

    assert data == result
