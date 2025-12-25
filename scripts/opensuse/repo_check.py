#!/usr/bin/env python3

import re
import sys
from typing import Final

import requests
from bs4 import BeautifulSoup

IMAGES_URL: Final = (
    f"https://download.opensuse.org/repositories/Cloud:/Images:/Leap_{sys.argv[1]}/images/"
)


def error(msg: str) -> None:
    print(msg, file=sys.stderr)  # noqa: T201
    sys.exit(1)


response = requests.get(IMAGES_URL, timeout=10)
try:
    response.raise_for_status()
except requests.HTTPError as err:
    error(f"HTTP error occurred: {err}")
soup = BeautifulSoup(response.content, "html.parser")
pattern = re.compile(r"openSUSE-Leap-15\.[56]\.x86_64-1\.0\.\d-NoCloud-Build\d{0,1}\.\d+\.qcow2")
res = soup.find("td", class_="name", string=pattern)
if res:
    print(res.get_text().strip())  # noqa: T201
else:
    error("No correct image!")
