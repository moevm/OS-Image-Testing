USER                       := user
GROUP                      := yoctogroup
OS_IMAGE                   := core-image-minimal
TEST_LAYER                 := meta-image-tests

# Docker
DOCKER_TAG                 := yocto-builder-image
DOCKER_BUILD_VOLUME        := yocto-build
DOCKER_DOWNLOADS_VOLUME    := yocto-downloads
DOCKER_SSTATE_VOLUME       := yocto-sstate
DOCKER_TESTS_VOLUME        := yocto-${TEST_LAYER}

# Paths
POKY_DIR                   := /home/${USER}/poky
BUILD_DIR                  := ${POKY_DIR}/build
LAYER_DIR                  := ${POKY_DIR}/${TEST_LAYER}
HOST_LAYERS_PATH           := ${CURDIR}/layers
HOST_CONF_PATH             := ${CURDIR}/conf


docker:
	docker build \
		--tag ${DOCKER_TAG} \
		--build-arg USER="${USER}" \
		--build-arg GROUP="${GROUP}" \
		--file scripts/Yocto-Image-Boot/Dockerfile .
	docker volume create ${DOCKER_BUILD_VOLUME}
	docker volume create ${DOCKER_DOWNLOADS_VOLUME}
	docker volume create ${DOCKER_SSTATE_VOLUME}
	docker volume create ${DOCKER_TESTS_VOLUME}
	docker run --rm --user root \
		--entrypoint "" \
		--volume ${DOCKER_BUILD_VOLUME}:/tmp-build \
		--volume ${DOCKER_DOWNLOADS_VOLUME}:/tmp-downloads \
		--volume ${DOCKER_SSTATE_VOLUME}:/tmp-sstate \
		--volume ${DOCKER_TESTS_VOLUME}:/tmp-${TEST_LAYER} \
		${DOCKER_TAG} \
		bash -c "mkdir -p /tmp-build/build /tmp-build/conf && \
			mkdir -p /tmp-downloads && \
			mkdir -p /tmp-sstate && \
			mkdir -p /tmp-${TEST_LAYER}/conf && \
			chown -R ${USER}:${GROUP} /tmp-build /tmp-downloads /tmp-sstate /tmp-${TEST_LAYER}"

docker-init-volumes:
	docker run -it --rm \
		--volume ${DOCKER_BUILD_VOLUME}:${BUILD_DIR} \
		--volume ${DOCKER_DOWNLOADS_VOLUME}:${POKY_DIR}/downloads \
		--volume ${DOCKER_SSTATE_VOLUME}:${POKY_DIR}/sstate-cache \
		--volume ${DOCKER_TESTS_VOLUME}:${LAYER_DIR} \
		--volume "${HOST_CONF_PATH}/local.conf:${BUILD_DIR}/conf/local.conf" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/conf/layer.conf:${LAYER_DIR}/conf/layer.conf" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/recipes-stress/stress-ng/stress-ng_1.0.0.bb:${LAYER_DIR}/recipes-stress/stress-ng/stress-ng_1.0.0.bb" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/recipes-stress/stress-ng/files:${LAYER_DIR}/recipes-stress/stress-ng/files" \
		${DOCKER_TAG} \
		bash -c "bitbake-layers add-layer ${LAYER_DIR} && bitbake ${OS_IMAGE}"

run-image: docker-init-volumes
	docker run -it --rm \
		--volume ${DOCKER_BUILD_VOLUME}:${BUILD_DIR} \
		--volume ${DOCKER_DOWNLOADS_VOLUME}:${POKY_DIR}/downloads \
		--volume ${DOCKER_SSTATE_VOLUME}:${POKY_DIR}/sstate-cache \
		--volume ${DOCKER_TESTS_VOLUME}:${LAYER_DIR} \
		--volume "${HOST_CONF_PATH}/local.conf:${BUILD_DIR}/conf/local.conf" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/conf/layer.conf:${LAYER_DIR}/conf/layer.conf" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/recipes-stress/stress-ng/stress-ng_1.0.0.bb:${LAYER_DIR}/recipes-stress/stress-ng/stress-ng_1.0.0.bb" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}/recipes-stress/stress-ng/files:${LAYER_DIR}/recipes-stress/stress-ng/files" \
		${DOCKER_TAG} \
		runqemu --config /home/${USER}/poky/build/tmp/deploy/images/qemux86-64/core-image-minimal-qemux86-64.rootfs.qemuboot.conf slirp nographic

help:
	@echo "Usage:"
	@echo "  make [targets] [arguments]"
	@echo
	@echo "  docker                 Builds a docker image;"
	@echo "  docker-init-volumes    Initializes docker volumes;"
	@echo "  run-image              Runs builded Yocto image from builded docker image;"
	@echo "  help                   Displays information about all available targets."


.PHONY: docker docker-init-volumes run-image
