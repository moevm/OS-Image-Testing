#!/bin/bash

SUSE_IMAGE=""

if [ "$1" = 15.5 ]; then
    SUSE_IMAGE="open-suse-15-5.qcow2"
elif [ "$1" = 15.6 ]; then
    SUSE_IMAGE="open-suse-15-6.qcow2"
else
{
    echo "Leap version is incorrect! Should be 15.5 or 15.6!"
    exit 1
}
fi

# NOTE: simplest os run, qemu's run configuration would be extended during developement
qemu-system-x86_64 $SUSE_IMAGE -m 4G -nographic
