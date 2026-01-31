#!/usr/bin/env bash

if [ -n "${GOOGLE_DNS:-}" ]; then
  echo "nameserver ${GOOGLE_DNS}" >> /etc/resolv.conf 2>/dev/null || true
fi

wget --timeout=10 --tries=1 "${GOOGLE_IP:-http://142.250.185.206/}" 2>&1
WGET_RESULT=$?

if [ "$WGET_RESULT" -eq 0 ]; then
    exit 0
else
    exit 1
fi
