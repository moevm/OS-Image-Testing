SUMMARY = "ChaosBlade CLI tool"
LICENSE = "Apache-2.0"
HOMEPAGE = "https://github.com/chaosblade-io/chaosblade"

CHAOSBLADE_VERSION = "1.8.0"

SRC_URI = "https://github.com/chaosblade-io/chaosblade/releases/download/v${CHAOSBLADE_VERSION}/chaosblade-${CHAOSBLADE_VERSION}-linux_amd64.tar.gz"
SRC_URI[sha256sum] = "a49bb08dfe2a2292c60600ad8e34bf922fe11449317a03c67120838f6e7ee236"

LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/Apache-2.0;md5=89aea4e17d99a7cacdbeed46a0096b10"

COMPATIBLE_MACHINE = "qemux86-64"

S = "${WORKDIR}/chaosblade-${CHAOSBLADE_VERSION}-linux_amd64"

inherit allarch

do_configure[noexec] = "1"
do_compile[noexec] = "1"

do_install() {
    bbnote "Установка ChaosBlade из ${S}"

    install -d ${D}/var/lib/chaosblade
    install -d ${D}${bindir}

    cp -r ${S}/* ${D}/var/lib/chaosblade/ 2>/dev/null || true

    ln -sf /var/lib/chaosblade/blade ${D}${bindir}/blade

    chmod 755 ${D}/var/lib/chaosblade/blade 2>/dev/null || true
}

FILES:${PN} = " \
    /var/lib/chaosblade/* \
    ${bindir}/blade \
"

RDEPENDS:${PN} = "bash"
INSANE_SKIP:${PN} = "arch ldflags already-stripped file-rdeps"
