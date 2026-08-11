#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/common.sh"

CHAOSBLADE_VERSION="${CHAOSBLADE_VERSION:-1.8.0}"
CPU_PERCENT="${CHAOSBLADE_CPU_PERCENT:-20}"
TIMEOUT="${CHAOSBLADE_TIMEOUT_SEC:-30}"
NET_DELAY_MS="${CHAOSBLADE_NETWORK_DELAY_MS:-}"
INTERFACE="${CHAOSBLADE_INTERFACE:-eth0}"

IDS=()

cleanup() {
    local id
    for id in "${IDS[@]}"; do
        run "$id" <<<"sudo /opt/chaosblade/blade destroy $id" || warn "Failed to destroy $id"
    done
}
trap cleanup EXIT

install_chao() {
    has blade && { info "chaosblade already installed on ${TARGET}"; return; }
    [[ "$TARGET" == yocto ]] && die "not installed on ${TARGET}; add the chaosblade to the poky image"
    info "Installing chaosblade v${CHAOSBLADE_VERSION} on ${TARGET}..."
    run "$CHAOSBLADE_VERSION" <<'EOF' || die "Failed to install chaosblade"
set -euo pipefail
v=$1
d=$(mktemp -d)
trap 'rm -rf "$d"' EXIT
cd "$d"
sudo zypper -n install --no-recommends wget tar
wget -q "https://github.com/chaosblade-io/chaosblade/releases/download/v${v}/chaosblade-${v}-linux_amd64.tar.gz"
tar -xzf "chaosblade-${v}-linux_amd64.tar.gz"
mkdir -p /opt/chaosblade
cp -r "chaosblade-${v}-linux_amd64"/. /opt/chaosblade/
chmod 755 /opt/chaosblade/blade
ln -sf /opt/chaosblade/blade /usr/local/bin/blade
EOF
}

create_exp() {
    local out id
    out=$(run "$@" <<'EOF'
set -euo pipefail
sudo /opt/chaosblade/blade check os "$1" "$2" > /dev/null 2>&1 || true
sudo /opt/chaosblade/blade create "$1" "$2" "${@:3}"
EOF
) || return 1
    id=$(printf '%s\n' "$out" | grep -o '"result":"[^"]*"' | head -1 | sed 's/"result":"\([^"]*\)"/\1/') || return 1
    [[ -n "$id" ]] || return 1
    printf '%s' "$id"
}

show()    { run "$1" <<<'sudo /opt/chaosblade/blade status "$1"'; }
destroy() { run "$1" <<<"sudo /opt/chaosblade/blade destroy $1" || warn "Failed to destroy $1"; }

main() {
    install_chao

    cpu=$(create_exp cpu fullload --cpu-percent "$CPU_PERCENT" --timeout "$TIMEOUT") ||
        die "Failed to create CPU experiment"
    IDS+=("$cpu")
    show "$cpu"
    info "Running CPU experiment for 5s..."
    sleep 5

    if [[ -n "$NET_DELAY_MS" ]]; then
        if net=$(create_exp network delay --time "$NET_DELAY_MS" --interface "$INTERFACE" --timeout "$TIMEOUT"); then
            IDS+=("$net")
            show "$net"
            info "Running network experiment for 5s..."
            sleep 5
            destroy "$net"
        else
            warn "Skipping network experiment"
        fi
    fi

    destroy "$cpu"
    show "$cpu"
    info "Done."
}
main "$@"
