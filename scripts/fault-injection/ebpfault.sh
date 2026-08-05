#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

DIR="${EBPFAULT_DIR:-/opt/ebpfault}"
VER="${EBPFAULT_VER:-1.1.2}"
SYSCALL="${EBPFAULT_SYSCALL:-fchmodat}"
ERRNO="${EBPFAULT_ERRNO:-ENOENT}"
PROB="${EBPFAULT_PROB:-50}"
ARGS="${EBPFAULT_ARGS:-/bin/chmod 0755 /tmp/ebpfault_marker}"

install_ebpf() {
    has "$DIR/bin/ebpfault" && { info "ebpfault already installed in ${DIR}"; return; }
    info "Installing ebpfault v${VER}..."
    run "$DIR" "$VER" <<'EOF' || die "Failed to install ebpfault."
set -euo pipefail
d=$1; v=$2
url="https://github.com/trailofbits/ebpfault/releases/download/v${v}/ebpfault-${v}-1.x86_64.tar.gz"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
wget -q -O "$tmp/ebpfault.tar.gz" "$url" || curl -fsSL -o "$tmp/ebpfault.tar.gz" "$url"
tar -xzf "$tmp/ebpfault.tar.gz" -C "$tmp"
sudo mkdir -p "$d"
sudo chown "$(id -u):$(id -g)" "$d"
cp -r "$tmp"/ebpfault-"${v}"-1.x86_64/. "$d"/
chmod +x "$d/bin/ebpfault"
EOF
}

kprobe_supported() {
    run <<'EOF'
{ zcat /proc/config.gz 2>/dev/null || cat "/boot/config-$(uname -r)" 2>/dev/null; } | grep -q '^CONFIG_BPF_KPROBE_OVERRIDE=y'
EOF
}

gen_config() {
    info "Writing ebpfault config (${SYSCALL} -> -${ERRNO}, ${PROB}%)..."
    run "$DIR" "$SYSCALL" "$ERRNO" "$PROB" <<'EOF' || die "Failed to write ebpfault config."
cat > "$1/config.json" <<JSON
{
  "fault_injectors": [
    { "syscall_name": "$2", "error_list": [ { "exit_code": "-$3", "probability": $4 } ] }
  ]
}
JSON
EOF
}

run_exp() {
    info "Running '${ARGS}' through ebpfault..."
    run "$DIR" <<EOF || true
set +e
touch /tmp/ebpfault_marker
chmod 0644 /tmp/ebpfault_marker
"\$1/bin/ebpfault" --config "\$1/config.json" --exec $ARGS
echo "exit_code=\$?"
EOF
}

main() {
    install_ebpf

    if ! kprobe_supported; then
        warn "CONFIG_BPF_KPROBE_OVERRIDE is not enabled in the kernel on ${TARGET}."
        warn "Enable it in a kernel config (layers/meta-image-tests/recipes-kernel/linux/linux-yocto/fault-injection.cfg) and rebuild the image."
        warn "Note that you can run this script only for Yocto."
        exit 1
    fi

    gen_config
    run_exp
    info "Done!"
}
main "$@"
