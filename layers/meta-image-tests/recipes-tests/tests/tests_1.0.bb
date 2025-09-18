SUMMARY = "My test with multiple ptest shell scripts"
LICENSE = "CLOSED"

SRC_URI = "file://tests-1.0/"

inherit ptest

RDEPENDS:${PN} += "bash perf"
RDEPENDS:${PN}-ptest += "perf bash findutils"

FILES_${PN} += "${datadir}/tests"

do_compile() {
    :
}

do_install() {
    install -d ${D}${datadir}/tests

    cp -r ${WORKDIR}/tests-1.0/* ${D}${datadir}/tests/
}

do_install_ptest() {
    install -d ${D}${PTEST_PATH}
    install -m 0755 ${S}/run-ptest ${D}${PTEST_PATH}
}

