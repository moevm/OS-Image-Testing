from __future__ import annotations

from textwrap import dedent

from imgtests.exec import osinfo


def test_parse_os_release_basic_fields():
    content = dedent(
        """
        # comment line
        ID="opensuse-leap"
        NAME="openSUSE Leap"
        VERSION_ID="15.5"
        PRETTY_NAME="openSUSE Leap 15.5"
        """
    )

    data = osinfo._parse_os_release(content)

    assert data["ID"] == "opensuse-leap"
    assert data["NAME"] == "openSUSE Leap"
    assert data["VERSION_ID"] == "15.5"
    assert data["PRETTY_NAME"] == "openSUSE Leap 15.5"


def test_parse_os_release_ignores_comments_and_blank_lines():
    content = dedent(
        """

        # first comment
        ID=ubuntu

           # indented comment
        NAME=Ubuntu

        """
    )

    data = osinfo._parse_os_release(content)

    assert data["ID"] == "ubuntu"
    assert data["NAME"] == "Ubuntu"
    assert set(data.keys()) == {"ID", "NAME"}


def test_parse_os_release_ignores_lines_without_equal():
    content = dedent(
        """
        ID=arch
        THIS IS MALFORMED
        NAME=Arch Linux
        """
    )

    data = osinfo._parse_os_release(content)

    assert data["ID"] == "arch"
    assert data["NAME"] == "Arch Linux"
    assert "THIS IS MALFORMED" not in data.keys()
    assert "THIS IS MALFORMED" not in data.values()
