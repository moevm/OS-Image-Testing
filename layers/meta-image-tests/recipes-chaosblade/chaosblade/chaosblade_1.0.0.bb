SUMMARY = "ChaosBlade CLI tool"
LICENSE = "Apache-2.0"

CHAOSBLADE_VERSION = "1.8.0"

SRC_URI = "https://github.com/chaosblade-io/chaosblade/releases/download/v${CHAOSBLADE_VERSION}/chaosblade-${CHAOSBLADE_VERSION}-linux_amd64.tar.gz"
SRC_URI[sha256sum] = "a49bb08dfe2a2292c60600ad8e34bf922fe11449317a03c67120838f6e7ee236"

LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/Apache-2.0;md5=89aea4e17d99a7cacdbeed46a0096b10"

COMPATIBLE_MACHINE = "(x86.*|.*64)"

S = "${WORKDIR}/chaosblade-${CHAOSBLADE_VERSION}-linux_amd64"

do_configure[noexec] = "1"
do_compile[noexec] = "1"

do_install() {
    install -d ${D}/opt/chaosblade
    install -d ${D}${bindir}

    cp -r ${S}/* ${D}/opt/chaosblade/

    ln -sf /opt/chaosblade/blade ${D}${bindir}/blade

    chmod 755 ${D}/opt/chaosblade/blade
}

FILES:${PN} = " \
    /opt/chaosblade/* \
    ${bindir}/blade \
"

INSANE_SKIP:${PN} = "already-stripped"
