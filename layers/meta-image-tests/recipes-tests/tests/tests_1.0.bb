SUMMARY = "Recipe with tests"
LICENSE = "CLOSED"

SRC_URI = "\
    file://tests/ \ 
    file://tests/performance/cpu/ \ 
    file://tests/performance/disks/ \
    file://tests/performance/memory/ \
    file://tests/performance/network/ \
"

inherit ptest

RDEPENDS:${PN} += "bash perf"
RDEPENDS:${PN}-ptest += "perf bash findutils"


FILES_${PN}-ptest += "${PTEST_PATH}"

do_compile() {
    :
}

do_install() {
    install -d ${D}${bindir}/tests
    touch ${D}${bindir}/tests/.keep
}

do_install_ptest() {
    install -d ${D}${PTEST_PATH}/tests/performance/disks
    cp -r ${WORKDIR}/tests/performance/disks/* ${D}${PTEST_PATH}/tests/performance/disks/
    
    install -d ${D}${PTEST_PATH}/tests/performance/cpu
    cp -r ${WORKDIR}/tests/performance/cpu/* ${D}${PTEST_PATH}/tests/performance/cpu/
    
    install -d ${D}${PTEST_PATH}/tests/performance/memory
    cp -r ${WORKDIR}/tests/performance/memory/* ${D}${PTEST_PATH}/tests/performance/memory/
    
    install -d ${D}${PTEST_PATH}/tests/performance/network
    cp -r ${WORKDIR}/tests/performance/network/* ${D}${PTEST_PATH}/tests/performance/network/
    
    install -m 0755 ${WORKDIR}/tests/run-ptest ${D}${PTEST_PATH}/run-ptest
}

