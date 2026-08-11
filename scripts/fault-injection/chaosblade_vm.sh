#!/bin/bash

set -euo pipefail

CHAOSBLADE_VERSION="${CHAOSBLADE_VERSION:-1.8.0}"
CPU_PERCENT="${CHAOSBLADE_CPU_PERCENT:-20}"
TIMEOUT="${CHAOSBLADE_TIMEOUT_SEC:-30}"
NET_DELAY_MS="${CHAOSBLADE_NETWORK_DELAY_MS:-}"
INTERFACE="${CHAOSBLADE_INTERFACE:-eth0}"

IDS=()

cleanup() {
    local id
    for id in "${IDS[@]}"; do
        sudo /opt/chaosblade/blade destroy "$id" || true
    done
}
trap cleanup EXIT

install_chao() {
    command -v blade && { echo "[INFO]  chaosblade already installed"; return; }
    echo "[INFO]  Installing chaosblade v${CHAOSBLADE_VERSION}..."
    d=$(mktemp -d)
    trap 'rm -rf "$d"' EXIT
    cd "$d"
    sudo zypper -n install --no-recommends wget tar
    wget -q "https://github.com/chaosblade-io/chaosblade/releases/download/v${CHAOSBLADE_VERSION}/chaosblade-${CHAOSBLADE_VERSION}-linux_amd64.tar.gz"
    tar -xzf "chaosblade-${CHAOSBLADE_VERSION}-linux_amd64.tar.gz"
    sudo mkdir -p /opt/chaosblade
    sudo cp -r "chaosblade-${CHAOSBLADE_VERSION}-linux_amd64"/. /opt/chaosblade/
    sudo chmod 755 /opt/chaosblade/blade
    sudo ln -sf /opt/chaosblade/blade /usr/local/bin/blade
}

create_exp() {
    sudo /opt/chaosblade/blade check os "$1" "$2" > /dev/null 2>&1 || true
    local out id
    out=$(sudo /opt/chaosblade/blade create "$1" "$2" "${@:3}")
    id=$(printf '%s\n' "$out" | grep -o '"result":"[^"]*"' | head -1 | sed 's/"result":"\([^"]*\)"/\1/')
    [[ -n "$id" ]] || return 1
    printf '%s' "$id"
}

show()    { sudo /opt/chaosblade/blade status "$1"; }
destroy() { sudo /opt/chaosblade/blade destroy "$1" || true; }

main() {
    install_chao

    local cpu net
    cpu=$(create_exp cpu fullload --cpu-percent "$CPU_PERCENT" --timeout "$TIMEOUT") ||
        { echo "[ERROR] Failed to create CPU experiment"; exit 1; }
    IDS+=("$cpu")
    show "$cpu"
    echo "[INFO]  Running CPU experiment for 5s..."
    sleep 5

    if [[ -n "$NET_DELAY_MS" ]]; then
        if net=$(create_exp network delay --time "$NET_DELAY_MS" --interface "$INTERFACE" --timeout "$TIMEOUT"); then
            IDS+=("$net")
            show "$net"
            echo "[INFO]  Running network experiment for 5s..."
            sleep 5
            destroy "$net"
        else
            echo "[WARN]  Skipping network experiment"
        fi
    fi

    destroy "$cpu"
    show "$cpu"
    echo "[INFO]  Done."
}
main "$@"
