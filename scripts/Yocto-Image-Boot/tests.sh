#!/bin/bash

POKY_DIR="/home/user/poky"
LAYER_DIR="${POKY_DIR}/meta-custom"
RECIPE_DIR="${LAYER_DIR}/recipes-stress/stress-ng"
BBAPPEND_FILE="${RECIPE_DIR}/stress-ng_%.bbappend"

source "${POKY_DIR}/oe-init-build-env" "${BUILD_DIR}"

bitbake-layers add-layer /home/user/poky/meta-custom

cat > "${LAYER_DIR}/conf/layer.conf" << 'EOF'
BBPATH .= ":${LAYERDIR}"
BBFILES += "${LAYERDIR}/recipes-*/*/*.bb ${LAYERDIR}/recipes-*/*/*.bbappend"
BBFILE_COLLECTIONS += "custom"
BBFILE_PATTERN_custom = "^${LAYERDIR}/"
BBFILE_PRIORITY_custom = "5"
LAYERSERIES_COMPAT_custom = "kirkstone"
EOF

cat > "${BBAPPEND_FILE}" << 'EOF'
inherit ptest
do_install_ptest() {
    install -d ${D}${PTEST_PATH}/tests
    
    cat > ${D}${PTEST_PATH}/tests/test-cpu-load.sh << 'EOF_A'
        #!/bin/sh
        echo "Starting CPU stress test for 10 seconds..."
        stress-ng --cpu 0 --timeout 10 --metrics --verify
        if [ $? -eq 0 ]; then
            echo "CPU test PASSED"
            exit 0
        else
            echo "CPU test FAILED"
            exit 1
        fi
EOF_A

    chmod +x ${D}${PTEST_PATH}/tests/test-cpu-load.sh

    cat > ${D}${PTEST_PATH}/run-ptest << 'EOF_B'
        #!/bin/sh
        cd $(dirname $0)
        echo "=== Running stress-ng ptest ==="
        PASS=0
        FAIL=0
        for test in tests/*.sh; do
            echo "TEST: $(basename $test)"
            ./$test && PASS=$((PASS+1)) || FAIL=$((FAIL+1))
        done
        echo "=== Summary: $PASS passed, $FAIL failed ==="
        [ $FAIL -eq 0 ] || exit 1
EOF_B

    chmod +x ${D}${PTEST_PATH}/run-ptest
}
EOF

if [ ! -f "${BBAPPEND_FILE}" ]; then
    echo "ERROR: File creation failed!"
    exit 1
fi

echo "SUCCESS: File created at ${BBAPPEND_FILE}!"
ls -la "${BBAPPEND_FILE}"
