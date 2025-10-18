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
"

RDEPENDS:${PN} = "wget stress-ng bash"
RDEPENDS:${PN}-ptest = "bash ptest-runner"

S = "${WORKDIR}/sources"
UNPACKDIR = "${S}"

ALLOW_EMPTY:${PN} = "1"

do_install_ptest() {
    install -d ${D}${PTEST_PATH}
    install -m 0755 ${S}/run-ptest ${D}${PTEST_PATH}/

    install -m 0755 ${S}/env.sh ${D}${PTEST_PATH}/

    install -d ${D}${PTEST_PATH}/tests/endurance/cpu
    install -m 0755 ${S}/endurance/cpu/test-cpu.sh ${D}${PTEST_PATH}/tests/endurance/cpu/

    install -d ${D}${PTEST_PATH}/tests/endurance/disks
    install -m 0755 ${S}/endurance/disks/test-disk.sh ${D}${PTEST_PATH}/tests/endurance/disks/
    
    install -d ${D}${PTEST_PATH}/tests/endurance/memory
    install -m 0755 ${S}/endurance/memory/test-memory.sh ${D}${PTEST_PATH}/tests/endurance/memory/

    install -d ${D}${PTEST_PATH}/tests/endurance/network    
    install -m 0755 ${S}/endurance/network/test-network.sh ${D}${PTEST_PATH}/tests/endurance/network/
}

FILES:${PN}-ptest += "${PTEST_PATH}/*"