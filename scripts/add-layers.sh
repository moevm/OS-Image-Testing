#!/bin/bash

LAYERS=($(find . -maxdepth 2 -type d -name "meta-*" | sort))

EXCLUDE_LAYERS=("meta-openembedded" "meta-secure-core")

for layer in "${LAYERS[@]}"; do
    layer="${layer#./}"
    layer_path="/home/user/poky/${layer}"

    skip=false
    for excluded in "${EXCLUDE_LAYERS[@]}"; do
        if [ "$layer" = "$excluded" ]; then
            echo "Skipping excluded layer: $layer"
            skip=true
            break
        fi
    done
    
    if [ "$skip" = true ]; then
        continue
    fi

    if [ -d "$layer_path" ]; then
        echo "Adding layer: $layer"
        bitbake-layers add-layer --quiet "$layer_path"
    else
        echo "Warning: Layer $layer not found!"
    fi
done