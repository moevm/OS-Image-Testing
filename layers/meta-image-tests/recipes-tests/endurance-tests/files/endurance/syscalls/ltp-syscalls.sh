#!/bin/sh
set -eu

OUT_DIR=/var/log/ltp
mkdir -p "$OUT_DIR"

STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="$OUT_DIR/ltp-syscalls-$STAMP.log"
OUT="$OUT_DIR/ltp-syscalls-$STAMP.out"

RUNLTP=/opt/ltp/runltp

echo "Starting LTP syscalls..."
if "$RUNLTP" -p -q -l "$LOG" -o "$OUT" -f syscalls; then
    echo "LTP syscalls PASSED"
    exit 0
else
    echo "LTP syscalls FAILED"
    exit 1
fi
