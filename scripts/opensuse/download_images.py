#!/usr/bin/env python3

import argparse
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger()


def error(msg: str) -> NoReturn:
    logger.error(msg)
    sys.exit(1)


def call_cmd(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, text=True, stderr=subprocess.PIPE)  # noqa: S603


def handle_result(result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode:
        error(result.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("suse_ver", help="OpenSUSE version.", choices=["15.5", "15.6"])
    return parser.parse_args()


def is_sha256sum_pass(target_file: Path, target_file_sha256: Path) -> bool:
    logger.info("Checking '%s' hash sum.", target_file)
    result = call_cmd(["sha256sum", "-c", str(target_file_sha256)])
    if result.returncode:
        target_file.unlink()
        target_file_sha256.unlink()
        return False
    return True


def download(suse_ver: str) -> None:
    target_file = Path(f"open-suse-{suse_ver}.qcow2")
    ready_file = target_file.with_suffix(".ready.qcow2")
    if ready_file.exists():
        logger.info("'%s' already exists.", ready_file)
        return
    target_file_sha256 = target_file.with_suffix(".sha256")
    if (
        target_file.exists()
        and target_file_sha256.exists()
        and is_sha256sum_pass(target_file, target_file_sha256)
    ):
        return
    images_url = (
        f"https://download.opensuse.org/repositories/Cloud:/Images:/Leap_{suse_ver}/images/"
    )
    response = requests.get(images_url, timeout=10)
    try:
        response.raise_for_status()
    except requests.HTTPError as err:
        error(f"HTTP error occurred: {err}")
    soup = BeautifulSoup(response.content, "html.parser")
    pattern = re.compile(
        r"openSUSE-Leap-15\.[56]\.x86_64-1\.0\.\d-NoCloud-Build\d{0,1}\.\d+\.qcow2"
    )
    res = soup.find("td", class_="name", string=pattern)
    if res:
        last_image = res.get_text().strip()
    else:
        error("No correct image!")
    image_url = f"{images_url}{last_image}"
    if not target_file.exists():
        logger.info("Downloading image '%s' ...", image_url)
        handle_result(
            call_cmd(
                ["wget", image_url, "-O", str(target_file), "--verbose", "--no-check-certificate"]
            )
        )
    if not target_file_sha256.exists():
        handle_result(
            call_cmd(
                [
                    "wget",
                    f"{image_url}.sha256",
                    "-O",
                    f"{target_file_sha256!s}",
                    "--no-check-certificate",
                ]
            )
        )
        handle_result(
            call_cmd(["sed", "-i", f"s/{last_image}/{target_file!s}/g", str(target_file_sha256)])
        )
    if not is_sha256sum_pass(target_file, target_file_sha256):
        error("sha256sum check failed.")
    target_file.rename(ready_file)
    target_file_sha256.unlink()


if __name__ == "__main__":
    download(parse_args().suse_ver)
