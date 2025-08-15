SUMMARY = "Stress-ng recipe"
LICENSE = "GPL-2.0-only"

S = "${WORKDIR}/git"
LIC_FILES_CHKSUM = "file://COPYING;md5=b234ee4d69f5fce4486a80fdaf4a4263"

SRC_URI = "git://github.com/ColinIanKing/stress-ng.git;protocol=https;branch=master"
SRCREV = "20e0f48cf0ca9cc96ed150c3dfa96f8e8a2f964b"

SRC_URI += " \
    file://run-ptest \
    file://endurance/cpu/test-cpu.sh \
    file://endurance/disks/test-disk.sh \
    file://endurance/memory/test-memory.sh \
    file://endurance/network/test-network.sh \
"

DEPENDS = "zlib libaio bash"
RDEPENDS:${PN} = "glibc"
RDEPENDS:${PN}-ptest += "bash"

inherit ptest

do_install() {
    install -Dm 0755 ${B}/stress-ng ${D}${bindir}/stress-ng
}

do_install_ptest() {
    install -m 0755 ${WORKDIR}/run-ptest ${D}${PTEST_PATH}

    install -d ${D}${PTEST_PATH}/tests/endurance/cpu
    install -m 0755 ${WORKDIR}/endurance/cpu/test-cpu.sh ${D}${PTEST_PATH}/tests/endurance/cpu

    install -d ${D}${PTEST_PATH}/tests/endurance/disks
    install -m 0755 ${WORKDIR}/endurance/disks/test-disk.sh ${D}${PTEST_PATH}/tests/endurance/disks
    
    install -d ${D}${PTEST_PATH}/tests/endurance/memory
    install -m 0755 ${WORKDIR}/endurance/memory/test-memory.sh ${D}${PTEST_PATH}/tests/endurance/memory

    install -d ${D}${PTEST_PATH}/tests/endurance/network    
    install -m 0755 ${WORKDIR}/endurance/network/test-network.sh ${D}${PTEST_PATH}/tests/endurance/network
}