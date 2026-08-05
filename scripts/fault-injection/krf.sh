#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

KRF_DIR="${KRF_DIR:-/opt/krf}"
SYSCALLS="${KRF_SYSCALLS:-write}"
PROB="${KRF_PROB:-1}"
PROFILE="${KRF_PROFILE:-}"
TARGET_CMD="${KRF_TARGET:-dd if=/dev/urandom of=/dev/null bs=64K count=512}"
LOADED=0

cleanup() {
    run <<EOF || true
sudo "$KRF_DIR/src/krfctl/krfctl" -c >/dev/null 2>&1 || true
sudo "$KRF_DIR/src/krfctl/krfctl" -C >/dev/null 2>&1 || true
EOF
    if (( LOADED )); then
        run <<'EOF' || true
sudo rmmod krfx >/dev/null 2>&1 || true
EOF
    fi
}
trap cleanup EXIT

missing() {
    run <<'EOF'
for tool in gcc make ruby; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "$tool"
    fi
done
if ! ls /lib/modules/*/build >/dev/null 2>&1; then
    echo "kernel headers"
fi
EOF
}

install_deps() {
    if [[ "$TARGET" == "suse" ]]; then
        info "Installing krf build deps on ${TARGET}."
        run <<'EOF' || die "Failed to install deps on ${TARGET}"
set -e
sudo zypper -n install --no-recommends gcc make libelf-devel ruby git-core kernel-default-devel
EOF
    else
        die "Missing dependencies cannot be installed to Poky in runtime. Please, add them to conf/packages.conf and rebuild image"
    fi
}

build_krf() {
    if has "$KRF_DIR/src/krfctl/krfctl"; then
        info "krf already built in ${KRF_DIR}"
        return
    fi
    info "Cloning and building krf in ${KRF_DIR}..."
    run "$KRF_DIR" <<'EOF' || die "krf build failed."
set -e
krf_dir="$1"
if [[ ! -d "$krf_dir" ]]; then
    sudo git clone --depth 1 https://github.com/trailofbits/krf "$krf_dir"
    sudo chown -R "$(id -u):$(id -g)" "$krf_dir"
fi
headers="/lib/modules/$(uname -r)/build"
if [[ ! -d "$headers" ]]; then
    headers=$(ls -d /lib/modules/*/build 2>/dev/null | head -1)
fi
if [[ -z "$headers" || ! -d "$headers" ]]; then
    echo "no kernel headers found"
    exit 1
fi
kver=$(basename "$(dirname "$headers")")
mkdir -p /tmp/krf-fakebin
cat > /tmp/krf-fakebin/uname <<'INNER'
#!/bin/bash
if [[ "$1" == "-r" ]]; then echo "__KVER__"; else /bin/uname "$@"; fi
INNER
sed -i "s/__KVER__/${kver}/" /tmp/krf-fakebin/uname
chmod +x /tmp/krf-fakebin/uname
export PATH="/tmp/krf-fakebin:$PATH"
make -C "$krf_dir/src/module/linux" codegen
make -C "$headers" M="$krf_dir/src/module/linux" modules
make PLATFORM=linux -C "$krf_dir/src/krfexec"
make PLATFORM=linux -C "$krf_dir/src/krfctl"
make PLATFORM=linux -C "$krf_dir/src/krfmesg"
EOF
}

load_module() {
    if run <<'EOF'
lsmod | grep -q '^krfx'
EOF
    then
        info "krfx module already loaded"
        return
    fi
    info "Loading krfx.ko..."
    run "$KRF_DIR" <<'EOF' || die "Failed to load krfx.ko."
set -e
sudo insmod -f "$1/src/module/linux/krfx.ko"
EOF
    LOADED=1
}

configure_krf() {
    info "Configuring krf (syscalls='${SYSCALLS}', prob=${PROB})..."
    run "$KRF_DIR" "$SYSCALLS" "$PROB" "$PROFILE" <<'EOF' || die "Failed to configure krf."
set -e
krfctl="$1/src/krfctl/krfctl"
sudo "$krfctl" -F "$2"
sudo "$krfctl" -T personality=28
sudo "$krfctl" -p "$3"
if [[ -n "${4:-}" ]]; then
    sudo "$krfctl" -P "${4:-}"
fi
echo 1 | sudo tee /proc/krf/log_faults >/dev/null
EOF
}

run_target() {
    info "Running '${TARGET_CMD}' through krfexec..."
    run <<EOF || true
"$KRF_DIR/src/krfexec/krfexec" $TARGET_CMD
echo "exit_code=\$?"
EOF
}

show_logs() {
    run <<'EOF' || true
sudo dmesg | grep -i "faulting" | tail -n 20
EOF
}

main() {
    local missing_list
    missing_list=$(missing) || true
    info "Missing prerequisites on ${TARGET}: ${missing_list:-none}"
    if [[ -n "$missing_list" ]]; then
        install_deps
        missing_list=$(missing) || true
        if [[ -n "$missing_list" ]]; then
            die "Still missing prerequisites: $missing_list"
        fi
    fi

    build_krf
    load_module
    configure_krf
    run_target
    show_logs
    info "Done!"
}
main "$@"
