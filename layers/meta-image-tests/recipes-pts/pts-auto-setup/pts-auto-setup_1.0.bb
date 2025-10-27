SUMMARY = "Startup script to fix DNS and install PTS tests"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://pts-autoinstall.sh"

inherit update-rc.d

INITSCRIPT_NAME = "pts-autoinstall"
INITSCRIPT_PARAMS = "defaults 99"

RDEPENDS:${PN} = "phoronix-test-suite"

do_install() {
    install -d ${D}${sysconfdir}/init.d
    install -m 0755 ${WORKDIR}/sources-unpack/pts-autoinstall.sh ${D}${sysconfdir}/init.d/${INITSCRIPT_NAME}
}

FILES:${PN} += "${sysconfdir}/init.d/${INITSCRIPT_NAME}"
