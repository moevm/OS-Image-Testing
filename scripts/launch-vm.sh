#!/bin/bash

if [ -z "$1" ]; then
    echo "Dir is required argument. Example: $0 /path/to/poky machine."
    exit 1
fi

POKY_DIR="$1"

if [ ! -d "$POKY_DIR" ]; then
    echo "Dir [$POKY_DIR] not found."
    exit 1
fi

if [ -z "$2" ]; then
    echo "Machine is required argument. Example: $0 /path/to/poky machine"
    exit 1
fi

MACHINE="$2"

DEPLOY_DIR="$POKY_DIR/build/tmp/deploy/images"

if [ ! -d "$DEPLOY_DIR" ]; then
    echo "Deploy dir [$DEPLOY_DIR] not found."
    echo "Build Yocto images first."
    exit 1
fi

if [ ! -d "$DEPLOY_DIR/$MACHINE" ]; then
    echo "Machine [$MACHINE] not found in $DEPLOY_DIR."
    echo "Make sure that the machine is correct and that the image has been created."
    exit 1
fi

# shellcheck disable=SC1091
source "$POKY_DIR/oe-init-build-env" "$POKY_DIR/build"

runqemu "$MACHINE"
