SUMMARY = "Autologin"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

ALLOW_EMPTY:${PN} = "1"

pkg_postinst:${PN}() {
    #!/bin/sh
    if [ -f "$D${sysconfdir}/inittab" ]; then
        sed -i 's|^S0:12345:respawn:/usr/sbin/ttyrun ttyS0 /bin/start_getty 115200 ttyS0 vt102|S0:12345:respawn:/bin/login -f root|' "$D${sysconfdir}/inittab"
    fi
}

pkg_postinst_ontarget:${PN}() {
    #!/bin/sh
    if [ -f "${sysconfdir}/inittab" ]; then
        sed -i 's|^S0:12345:respawn:/usr/sbin/ttyrun ttyS0 /bin/start_getty 115200 ttyS0 vt102|S0:12345:respawn:/bin/login -f root|' "${sysconfdir}/inittab"
    fi
}