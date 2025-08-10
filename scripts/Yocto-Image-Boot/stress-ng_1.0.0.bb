SUMMARY = "Stress-ng recipe"
LICENSE = "GPL-2.0-only"

S = "${WORKDIR}/git"
LIC_FILES_CHKSUM = "file://COPYING;md5=b234ee4d69f5fce4486a80fdaf4a4263"

SRC_URI = "git://github.com/ColinIanKing/stress-ng.git;protocol=https;branch=master"
SRCREV = "20e0f48cf0ca9cc96ed150c3dfa96f8e8a2f964b"

DEPENDS = "zlib libaio"
RDEPENDS:${PN} = "glibc"

inherit ptest

do_install() {
    install -Dm 0755 ${B}/stress-ng ${D}${bindir}/stress-ng
}

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