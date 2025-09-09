SUMMARY = "Autologin"
LICENSE = "GPL-2.0-only"

inherit core-image

IMAGE_FEATURES += " \
    debug-tweaks \
"

autologin () {    
    sed -i 's|^S0:12345:respawn:/bin/start_getty 115200 ttyS0 vt102|S0:12345:respawn:/bin/login -f root|' \
        ${IMAGE_ROOTFS}${sysconfdir}/inittab
        
    sed -i 's/^root:[^:]*:/root::/' ${IMAGE_ROOTFS}${sysconfdir}/passwd
}

ROOTFS_POSTPROCESS_COMMAND += "autologin; "