#!/bin/bash

set -euo pipefail

info() { printf '[INFO]  %s\n' "$*"; }
warn() { printf '[WARN]  %s\n' "$*" >&2; }
die()  { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

TARGET="${TARGET:-${1:-}}"
case "$TARGET" in
    yocto)
        SSH_ADDR="${SSH_YOCTO_ADDR:?SSH_YOCTO_ADDR}"
        SSH_USER="${SSH_YOCTO_USER:?SSH_YOCTO_USER}"
        SSH_PASS="${SSH_YOCTO_PASS:-}"
        SSH_PORT="${SSH_YOCTO_PORT:?SSH_YOCTO_PORT}"
        ;;
    suse)
        SSH_ADDR="${SSH_SUSE_ADDR_156:?SSH_SUSE_ADDR_156}"
        SSH_USER="${SSH_SUSE_USER:?SSH_SUSE_USER}"
        SSH_PASS="${SSH_SUSE_PASS:-}"
        SSH_PORT="${SSH_SUSE_PORT_156:?SSH_SUSE_PORT_156}"
        ;;
    *) die "TARGET must be 'yocto' or 'suse' (env TARGET or first arg).";;
esac

ssh_cmd() {
    local base=(ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)
    if command -v sshpass >/dev/null 2>&1; then
        sshpass -p "$SSH_PASS" "${base[@]}" -p "$SSH_PORT" -l "$SSH_USER" "$SSH_ADDR" "$@"
    else
        "${base[@]}" -p "$SSH_PORT" -l "$SSH_USER" "$SSH_ADDR" "$@"
    fi
}

SUDO_SETUP='if [[ "$(id -u)" -eq 0 ]]; then sudo() { "$@"; }; fi'

run() {
    { printf '%s\n' "$SUDO_SETUP"; cat; } | ssh_cmd bash -s -- "$@"
}

has() {
    run "$1" <<<'command -v "$1" >/dev/null 2>&1'
}
