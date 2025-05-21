#!/bin/bash

source /home/user/poky/oe-init-build-env

# rm -rf tmp

bitbake core-image-minimal

runqemu qemux86-64