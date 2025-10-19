SUMMARY = "Recipe with tests"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

inherit ptest

SRC_URI = "\
    file://tests/ \ 
    file://tests/performance/cpu/ \ 
    file://tests/performance/disks/ \
    file://tests/performance/memory/ \
    file://tests/performance/network/ \
"

RDEPENDS:${PN} += "bash perf stress-ng"
RDEPENDS:${PN}-ptest += "perf bash stress-ng"


FILES_${PN}-ptest += "${PTEST_PATH}"

SRCDIR = "${WORKDIR}/sources"
UNPACKDIR = "${SRCDIR}"

do_compile() {
    :
}

do_install() {
    install -d ${D}${bindir}/tests
    touch ${D}${bindir}/tests/.keep
}

do_install_ptest() {
    install -d ${D}${PTEST_PATH}/tests/performance/disks
    cp -r ${SRCDIR}/tests/performance/disks/* ${D}${PTEST_PATH}/tests/performance/disks/
    
    install -d ${D}${PTEST_PATH}/tests/performance/cpu
    cp -r ${SRCDIR}/tests/performance/cpu/* ${D}${PTEST_PATH}/tests/performance/cpu/
    
    install -d ${D}${PTEST_PATH}/tests/performance/memory
    cp -r ${SRCDIR}/tests/performance/memory/* ${D}${PTEST_PATH}/tests/performance/memory/
    
    install -d ${D}${PTEST_PATH}/tests/performance/network
    cp -r ${SRCDIR}/tests/performance/network/* ${D}${PTEST_PATH}/tests/performance/network/
    
    install -m 0755 ${SRCDIR}/tests/run-ptest ${D}${PTEST_PATH}/run-ptest
}

