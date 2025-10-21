SUMMARY = "Firmware tests for Linux"
DESCRIPTION = "Tests for firmware interfaces (ACPI, UEFI, SMBIOS) on Linux."
HOMEPAGE = "https://wiki.ubuntu.com/FirmwareTestSuite"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/GPL-2.0-only;md5=801f80980d171dd6425610833a22dbe6"

PV = "22.11.00"

SRC_URI = "http://fwts.ubuntu.com/release/fwts-V${PV}.tar.gz;subdir=${BP}"
SRC_URI[sha256sum] = "4af4e1e0f1ae9313297af722d744ba47a81c81bc5bdeab3f4f40837a39e4b808"

inherit autotools pkgconfig

DEPENDS = "libpcre glib-2.0 dtc bison-native flex-native libbsd"
RDEPENDS:${PN} += "dtc"

EXTRA_OEMAKE += 'AM_CFLAGS="-Wno-error -Wno-error=enum-int-mismatch"'

FILES:${PN} += " \
  ${datadir}/bash-completion/completions/fwts \
  ${libdir}/fwts/lib*${SOLIBS} \
"
FILES:${PN}-dev += "${libdir}/fwts/lib*${SOLIBSDEV} ${libdir}/fwts/lib*.la"
FILES:${PN}-staticdev += "${libdir}/fwts/lib*a"

