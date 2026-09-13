#!/bin/bash

set -e

./scripts/download_images.py "$1"
./scripts/cloud-setup.sh "${S_USER}" "${PASSWORD}"
echo "Image is ready. VM will be started by imgtests-suse-vm container."
