SUMMARY = "Stress tests using stress-ng and wget"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

inherit ptest

SRC_URI = " \
    file://run-ptest \
    file://env.sh \
    file://endurance/cpu/test-cpu.sh \
    file://endurance/disks/test-disk.sh \
    file://endurance/memory/test-memory.sh \
    file://endurance/network/test-network.sh \
    file://endurance/syscalls/ltp-syscalls.sh \
"

RDEPENDS:${PN} = "wget stress-ng bash"
RDEPENDS:${PN}-ptest = "bash ptest-runner"

SRCDIR = "${WORKDIR}/sources"
UNPACKDIR = "${SRCDIR}"

ALLOW_EMPTY:${PN} = "1"

do_install_ptest() {
    install -d ${D}${PTEST_PATH}
    install -m 0755 ${SRCDIR}/run-ptest ${D}${PTEST_PATH}/

    install -m 0755 ${SRCDIR}/env.sh ${D}${PTEST_PATH}/

    install -d ${D}${PTEST_PATH}/tests/endurance/cpu
    install -m 0755 ${SRCDIR}/endurance/cpu/test-cpu.sh ${D}${PTEST_PATH}/tests/endurance/cpu/

    install -d ${D}${PTEST_PATH}/tests/endurance/disks
    install -m 0755 ${SRCDIR}/endurance/disks/test-disk.sh ${D}${PTEST_PATH}/tests/endurance/disks/

    install -d ${D}${PTEST_PATH}/tests/endurance/memory
    install -m 0755 ${SRCDIR}/endurance/memory/test-memory.sh ${D}${PTEST_PATH}/tests/endurance/memory/

    install -d ${D}${PTEST_PATH}/tests/endurance/network
    install -m 0755 ${SRCDIR}/endurance/network/test-network.sh ${D}${PTEST_PATH}/tests/endurance/network/

    install -d ${D}${PTEST_PATH}/tests/endurance/syscalls
    install -m 0755 ${SRCDIR}/endurance/syscalls/ltp-syscalls.sh ${D}${PTEST_PATH}/tests/endurance/syscalls/
}

FILES:${PN}-ptest += "${PTEST_PATH}/*"
