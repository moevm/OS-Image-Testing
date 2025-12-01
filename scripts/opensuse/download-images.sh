#!/bin/bash

SUSE_DIST_URL="https://download.opensuse.org/repositories/Cloud:/Images:/Leap_""$1""/images/"

SUSE_15_5_IMG_FN="openSUSE-Leap-15.5.x86_64-1.0.1-NoCloud-Build6.180.qcow2"
SUSE_15_6_IMG_FN="openSUSE-Leap-15.6.x86_64-1.0.2-NoCloud-Build1.78.qcow2"

download () {
    # original file
    if [ ! -e "$2" ]; then
        wget "${SUSE_DIST_URL}""$1" -O "$2" --no-check-certificate
    fi

    # check sum
    if [ ! -e "$2".sha256 ]; then
        wget "${SUSE_DIST_URL}""$1".sha256 -O "$2".sha256 --no-check-certificate
        sed -i s/"$1"/"$2"/g "$2".sha256

        echo "Check sum status: "

        if ! sha256sum -c "$2".sha256; then
            rm "$2" "$2".sha256
            exit 2
        fi
    fi
}

if [ "$1" = 15.5 ]; then
    download ${SUSE_15_5_IMG_FN} "open-suse-""$1"".qcow2"
elif [ "$1" = 15.6 ]; then
    download ${SUSE_15_6_IMG_FN} "open-suse-""$1"".qcow2"
else
    echo "Leap version is incorrect! Should be 15.5, 15.6 or both"
    exit 1
fi
