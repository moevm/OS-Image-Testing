#!/bin/bash

SUSE_15_5_IMG_URL="https://download.opensuse.org/distribution/leap/15.5/appliances/openSUSE-Leap-15.5-Minimal-VM.x86_64-15.5.0-kvm-and-xen-Build13.309.qcow2"
SUSE_15_6_IMG_URL="https://download.opensuse.org/distribution/leap/15.6/appliances/openSUSE-Leap-15.6-Minimal-VM.x86_64-15.6.0-kvm-and-xen-Build17.45.qcow2"

SUSE_15_5_IMG="open-suse-15-5.qcow2"
SUSE_15_6_IMG="open-suse-15-6.qcow2"

if [ "$1" = 15.5 ]; then
    if [ ! -e $SUSE_15_5_IMG ]; then
        wget $SUSE_15_5_IMG_URL -O $SUSE_15_5_IMG --no-check-certificate
    fi
elif [ "$1" = 15.6 ]; then
    if [ ! -e $SUSE_15_6_IMG ]; then
        wget $SUSE_15_6_IMG_URL -O $SUSE_15_6_IMG --no-check-certificate
    fi
elif [ "$1" = "both" ]; then
{
    if [ ! -e $SUSE_15_5_IMG ]; then
        wget $SUSE_15_5_IMG_URL -O $SUSE_15_5_IMG --no-check-certificate
    fi

    if [ ! -e $SUSE_15_6_IMG ]; then
        wget $SUSE_15_6_IMG_URL -O $SUSE_15_6_IMG --no-check-certificate
    fi
}
else
{
    echo "Leap version is incorrect! Should be 15.5, 15.6 or both"
    exit 1
}
fi
