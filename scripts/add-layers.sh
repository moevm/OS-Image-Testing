#!/bin/bash

LAYERS=(
    "meta-image-tests"
    "meta-clang"
    "meta-dpdk"
    "meta-erlang"
    "meta-openembedded/meta-oe"
    "meta-openembedded/meta-python"
    "meta-openembedded/meta-networking"
    "meta-openembedded/meta-perl"
    "meta-openembedded/meta-initramfs"
    "meta-openembedded/meta-filesystems"
    "meta-openembedded/meta-multimedia"
    "meta-openembedded/meta-webserver"
    "meta-openembedded/meta-gnome"
    "meta-openembedded/meta-xfce"
    "meta-qt5"
    "meta-secure-core/meta-signing-key"
    "meta-secure-core/meta-ids"
    "meta-secure-core/meta-secure-core-common"
    "meta-secure-core/meta-efi-secure-boot"
    "meta-secure-core/meta-tpm2"
    "meta-secure-core/meta-encrypted-storage"
    "meta-secure-core/meta-integrity"
    "meta-security"
    "meta-virtualization"
    "meta-cloud-services"
    "meta-openjdk-temurin"
)

for layer in "${LAYERS[@]}"; do
    layer="${layer#./}"
    layer_path="/home/user/poky/${layer}"

    if [ -d "$layer_path" ]; then
        echo "Adding layer: $layer"
        bitbake-layers add-layer --quiet "$layer_path"
    else
        echo "Warning: Layer $layer not found!"
    fi
done

rm -rf /home/user/poky/meta-openjdk-temurin/recipes-java/helloworld-java
