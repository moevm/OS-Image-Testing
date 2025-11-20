#!/bin/bash

sudo service ssh start

# shellcheck disable=SC1091
source "/home/user/poky/oe-init-build-env" "/home/user/poky/build"
exec "$@"
