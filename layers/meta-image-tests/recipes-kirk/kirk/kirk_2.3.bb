SUMMARY = "Linux Test Project executor (CLI)"
HOMEPAGE = "https://github.com/linux-test-project/kirk"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://LICENSE;md5=39bba7d2cf0ba1036f2a6e2be52fe3f0"

PYPI_PACKAGE = "kirk"
SRC_URI[sha256sum] = "b14a86b847ce4269cbd179077be678377c9fbe8999da99ce9276d4af859a4ca4"

inherit pypi python_setuptools_build_meta

RDEPENDS:${PN} += " \
    python3-core \
    python3-modules \
"

RRECOMMENDS:${PN} += " \
    python3-msgpack \
"

do_install:append() {
    install -d ${D}${PYTHON_SITEPACKAGES_DIR}/libkirk/channels
    if [ -d ${S}/libkirk/channels ]; then
        cp ${S}/libkirk/channels/*.py \
           ${D}${PYTHON_SITEPACKAGES_DIR}/libkirk/channels/
    fi
}
