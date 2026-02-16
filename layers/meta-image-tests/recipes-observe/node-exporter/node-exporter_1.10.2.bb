SUMMARY = "Prometheus Node Exporter"
DESCRIPTION = "Prometheus exporter for hardware and OS metrics exposed by *NIX kernels"
LICENSE = "Apache-2.0"
LIC_FILES_CHKSUM = "file://LICENSE;md5=86d3f3a95c324c9479bd8986968f4327"

SRC_URI = " \
    https://github.com/prometheus/node_exporter/releases/download/v${PV}/node_exporter-${PV}.linux-amd64.tar.gz \
    file://node_exporter.init \
"
SRC_URI[sha256sum] = "c46e5b6f53948477ff3a19d97c58307394a29fe64a01905646f026ddc32cb65b"

S = "${WORKDIR}/node_exporter-${PV}.linux-amd64"

inherit update-rc.d

INITSCRIPT_NAME = "node_exporter"
INITSCRIPT_PARAMS = "stop 20 0 1 6 ."

do_install() {
    install -d ${D}/usr/local/bin
    install -m 0744 ${S}/node_exporter ${D}/usr/local/bin/

    install -d ${D}${sysconfdir}/init.d
    install -m 0744 ${UNPACKDIR}/node_exporter.init ${D}${sysconfdir}/init.d/${INITSCRIPT_NAME}
}

FILES:${PN} += "/usr/local/bin/node_exporter"

INSANE_SKIP:${PN} += "ldflags already-stripped"
