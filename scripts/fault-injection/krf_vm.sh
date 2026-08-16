#!/bin/bash

set -euo pipefail

KRF_DIR="${KRF_DIR:-/opt/krf}"
SYSCALLS="${KRF_SYSCALLS:-write}"
PROB="${KRF_PROB:-1}"
PROFILE="${KRF_PROFILE:-}"
TARGET_CMD="${KRF_TARGET:-dd if=/dev/urandom of=/dev/null bs=64K count=512}"
LOADED=0

cleanup() {
    sudo "$KRF_DIR/src/krfctl/krfctl" -c >/dev/null 2>&1 || true
    sudo "$KRF_DIR/src/krfctl/krfctl" -C >/dev/null 2>&1 || true
    if (( LOADED )); then
        sudo rmmod krfx >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

missing() {
    for tool in gcc make ruby; do
        command -v "$tool" >/dev/null 2>&1 || echo "$tool"
    done
    ls /lib/modules/*/build >/dev/null 2>&1 || echo "kernel headers"
}

install_deps() {
    sudo zypper -n install --no-recommends gcc make libelf-devel ruby git-core kernel-default-devel
}

build_krf() {
    if [[ -x "$KRF_DIR/src/krfctl/krfctl" ]]; then
        echo "[INFO]  krf already built in ${KRF_DIR}"
        return
    fi
    echo "[INFO]  Cloning and building krf in ${KRF_DIR}..."
    if [[ ! -d "$KRF_DIR" ]]; then
        sudo git clone --depth 1 https://github.com/trailofbits/krf "$KRF_DIR"
        sudo chown -R "$(id -u):$(id -g)" "$KRF_DIR"
    fi
    headers="/lib/modules/$(uname -r)/build"
    if [[ ! -d "$headers" ]]; then
        # shellcheck disable=SC2012
        headers=$(ls -d /lib/modules/*/build 2>/dev/null | head -1)
    fi
    if [[ -z "$headers" || ! -d "$headers" ]]; then
        echo "no kernel headers found"
        exit 1
    fi
    kver=$(basename "$(dirname "$headers")")
    echo "building against kernel headers: ${kver}"
    mkdir -p /tmp/krf-fakebin
    cat > /tmp/krf-fakebin/uname <<'INNER'
#!/bin/bash
if [[ "$1" == "-r" ]]; then echo "__KVER__"; else /bin/uname "$@"; fi
INNER
    sed -i "s/__KVER__/${kver}/" /tmp/krf-fakebin/uname
    chmod +x /tmp/krf-fakebin/uname
    export PATH="/tmp/krf-fakebin:$PATH"
    make -C "$KRF_DIR/src/module/linux" codegen
    make -C "$headers" M="$KRF_DIR/src/module/linux" modules
    make PLATFORM=linux -C "$KRF_DIR/src/krfexec"
    make PLATFORM=linux -C "$KRF_DIR/src/krfctl"
    make PLATFORM=linux -C "$KRF_DIR/src/krfmesg"
}

load_module() {
    if lsmod | grep -q '^krfx'; then
        echo "[INFO]  krfx module already loaded"
        return
    fi
    echo "[INFO]  Loading krfx.ko (force; built against non-running kernel headers)..."
    sudo insmod -f "$KRF_DIR/src/module/linux/krfx.ko"
    LOADED=1
}

configure_krf() {
    echo "[INFO]  Configuring krf (syscalls='${SYSCALLS}', prob=${PROB})..."
    krfctl="$KRF_DIR/src/krfctl/krfctl"
    sudo "$krfctl" -F "$SYSCALLS"
    sudo "$krfctl" -T personality=28
    sudo "$krfctl" -p "$PROB"
    if [[ -n "$PROFILE" ]]; then
        sudo "$krfctl" -P "$PROFILE"
    fi
    echo 1 | sudo tee /proc/krf/log_faults >/dev/null
}

run_target() {
    echo "[INFO]  Running '${TARGET_CMD}' through krfexec..."
    set +e
    "$KRF_DIR/src/krfexec/krfexec" "$TARGET_CMD"
    echo "exit_code=$?"
    set -e
}

show_logs() {
    sudo dmesg | grep -i "faulting" | tail -n 20
}

main() {
    local missing_list
    missing_list=$(missing)
    echo "[INFO]  Missing prerequisites: ${missing_list:-none}"
    if [[ -n "$missing_list" ]]; then
        install_deps
        missing_list=$(missing)
        if [[ -n "$missing_list" ]]; then
            echo "[ERROR] Still missing prerequisites: $missing_list"
            exit 1
        fi
    fi

    build_krf
    load_module
    configure_krf
    run_target
    show_logs
    echo "[INFO]  Done!"
}
main "$@"
