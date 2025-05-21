#!/bin/bash

echo "Копирование файлов из $(pwd)/build в volume yocto-build"

docker run --rm -v "yocto-build":/volume -v "$(pwd)/build":/source alpine \
    sh -c "cp -r /source/. /volume/ && chown -R 1010:0 /volume"

echo "Файлы успешно скопированы в том"