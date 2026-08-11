#!/bin/bash

set -euo pipefail

DIR="${EBPFAULT_DIR:-/opt/ebpfault}"
VER="${EBPFAULT_VER:-1.1.2}"
SYSCALL="${EBPFAULT_SYSCALL:-fchmodat}"
ERRNO="${EBPFAULT_ERRNO:-ENOENT}"
PROB="${EBPFAULT_PROB:-50}"
ARGS="${EBPFAULT_ARGS:-/bin/chmod 0755 /tmp/ebpfault_marker}"

install_ebpf() {
    if [[ -x "$DIR/bin/ebpfault" ]]; then
        echo "[INFO]  ebpfault already installed in ${DIR}"
        return
    fi
    echo "[INFO]  Installing ebpfault v${VER}..."
    url="https://github.com/trailofbits/ebpfault/releases/download/v${VER}/ebpfault-${VER}-1.x86_64.tar.gz"
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT
    wget -q -O "$tmp/ebpfault.tar.gz" "$url" || curl -fsSL -o "$tmp/ebpfault.tar.gz" "$url"
    tar -xzf "$tmp/ebpfault.tar.gz" -C "$tmp"
    sudo mkdir -p "$DIR"
    sudo chown "$(id -u):$(id -g)" "$DIR"
    cp -r "$tmp"/ebpfault-"${VER}"-1.x86_64/. "$DIR"/
    chmod +x "$DIR/bin/ebpfault"
}

kprobe_supported() {
    { zcat /proc/config.gz 2>/dev/null || cat "/boot/config-$(uname -r)" 2>/dev/null; } | grep -q '^CONFIG_BPF_KPROBE_OVERRIDE=y'
}

gen_config() {
    echo "[INFO]  Writing ebpfault config (${SYSCALL} -> -${ERRNO}, ${PROB}%)..."
    cat > "$DIR/config.json" <<JSON
{
  "fault_injectors": [
    { "syscall_name": "$SYSCALL", "error_list": [ { "exit_code": "-$ERRNO", "probability": $PROB } ] }
  ]
}
JSON
}

run_exp() {
    echo "[INFO]  Running '${ARGS}' through ebpfault..."
    set +e
    touch /tmp/ebpfault_marker
    chmod 0644 /tmp/ebpfault_marker
    "$DIR/bin/ebpfault" --config "$DIR/config.json" --exec $ARGS
    echo "exit_code=$?"
    set -e
}

main() {
    install_ebpf

    if ! kprobe_supported; then
        echo "[WARN]  CONFIG_BPF_KPROBE_OVERRIDE is not enabled in the kernel."
        echo "[WARN]  Enable it in a kernel config and rebuild the image."
        exit 1
    fi

    gen_config
    run_exp
    echo "[INFO]  Done!"
}
main "$@"
