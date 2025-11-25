#!/bin/bash

TESTFILES_DIR="/tmp/testfiles"
CONF_DIR="$(dirname "$0")/conf-fio"

mkdir -p $TESTFILES_DIR

fio "$CONF_DIR/scaling.fio"

rm -rf $TESTFILES_DIR
