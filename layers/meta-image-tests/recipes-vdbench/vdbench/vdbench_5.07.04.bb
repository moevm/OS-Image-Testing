SUMMARY = "Vdbench"
# License must be withing the archive and md5sum should be updated.
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://LICENSE;md5=8a1984b6adf89397460816c68c05c616"

FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://vdbench.tar.gz"

S = "${WORKDIR}/vdbench"

RDEPENDS:${PN} += "bash"

do_install() {
	install -d ${D}${bindir}/vdbench

	cp -r ${S}/* ${D}${bindir}/vdbench/
}

FILES:${PN} = "${bindir}/vdbench"
