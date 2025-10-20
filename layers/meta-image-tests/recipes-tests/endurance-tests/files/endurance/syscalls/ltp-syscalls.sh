#!/bin/sh
set -eu

OUT_DIR=/var/log/ltp
mkdir -p "$OUT_DIR"

STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="$OUT_DIR/ltp-syscalls-$STAMP.log"
OUT="$OUT_DIR/ltp-syscalls-$STAMP.out"

RUNLTP=/opt/ltp/runltp

"$RUNLTP" -p -q -l "$LOG" -o "$OUT" -f syscalls || true

echo "LTP syscalls finished (see $LOG, $OUT)"

