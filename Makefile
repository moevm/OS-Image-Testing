USER                       := user
GROUP                      := yoctogroup
OS_IMAGE                   := core-image-minimal
TEST_LAYER                 := meta-image-tests

# Docker
DOCKER_TAG                 := yocto-builder-image
DOCKER_BUILD_VOLUME        := yocto-build
DOCKER_DOWNLOADS_VOLUME    := yocto-downloads
DOCKER_SSTATE_VOLUME       := yocto-sstate

# Paths
POKY_DIR                   := /home/${USER}/poky
BUILD_DIR                  := ${POKY_DIR}/build
LAYER_DIR                  := ${POKY_DIR}/${TEST_LAYER}
HOST_LAYERS_PATH           := ${CURDIR}/layers
HOST_CONF_PATH             := ${CURDIR}/conf
HOST_SCRIPTS_PATH          := ${CURDIR}/scripts
HOST_TEMP_PATH             := ${CURDIR}/results

docker:
	docker build \
		--tag ${DOCKER_TAG} \
		--build-arg USER="${USER}" \
		--build-arg GROUP="${GROUP}" \
		--file docker/image_builder.dockerfile .
	docker volume create ${DOCKER_BUILD_VOLUME}
	docker volume create ${DOCKER_DOWNLOADS_VOLUME}
	docker volume create ${DOCKER_SSTATE_VOLUME}
	docker run --rm --user root \
		--entrypoint "" \
		--volume ${DOCKER_BUILD_VOLUME}:/tmp-build \
		--volume ${DOCKER_DOWNLOADS_VOLUME}:/tmp-downloads \
		--volume ${DOCKER_SSTATE_VOLUME}:/tmp-sstate \
		${DOCKER_TAG} \
		bash -c "mkdir -p /tmp-build/build /tmp-build/conf && \
			mkdir -p /tmp-downloads && \
			mkdir -p /tmp-sstate && \
			chown -R ${USER}:${GROUP} /tmp-build /tmp-downloads /tmp-sstate"

docker-init-volumes:
	docker run -it --rm \
		--volume ${DOCKER_BUILD_VOLUME}:${BUILD_DIR} \
		--volume ${DOCKER_DOWNLOADS_VOLUME}:${POKY_DIR}/downloads \
		--volume ${DOCKER_SSTATE_VOLUME}:${POKY_DIR}/sstate-cache \
		--volume "${HOST_CONF_PATH}/local.conf:${BUILD_DIR}/conf/local.conf" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}:${LAYER_DIR}" \
		${DOCKER_TAG} \
		bash -c "bitbake-layers add-layer ${LAYER_DIR} && bitbake ${OS_IMAGE}"

docker-run-image: docker-init-volumes
	docker run -it --rm \
		--volume ${DOCKER_BUILD_VOLUME}:${BUILD_DIR} \
		--volume ${DOCKER_DOWNLOADS_VOLUME}:${POKY_DIR}/downloads \
		--volume ${DOCKER_SSTATE_VOLUME}:${POKY_DIR}/sstate-cache \
		--volume "${HOST_CONF_PATH}/local.conf:${BUILD_DIR}/conf/local.conf" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}:${LAYER_DIR}" \
		${DOCKER_TAG} \
		runqemu qemux86-64 slirp nographic

docker-test-image: docker-init-volumes
	@echo "Starting QEMU test..."
	@mkdir -p ${HOST_TEMP_PATH}; \
	chmod 757 "${HOST_TEMP_PATH}"; \
	CONTAINER_ID=$$(docker run -d --rm \
		--volume ${DOCKER_BUILD_VOLUME}:${BUILD_DIR} \
		--volume ${DOCKER_DOWNLOADS_VOLUME}:${POKY_DIR}/downloads \
		--volume ${DOCKER_SSTATE_VOLUME}:${POKY_DIR}/sstate-cache \
		--volume "${HOST_CONF_PATH}/local.conf:${BUILD_DIR}/conf/local.conf" \
		--volume "${HOST_LAYERS_PATH}/${TEST_LAYER}:${LAYER_DIR}" \
		--volume "${HOST_TEMP_PATH}:/tmp/results" \
		--volume "${HOST_SCRIPTS_PATH}:/tmp/scripts" \
		${DOCKER_TAG} \
		bash /tmp/scripts/run-qemu-test.sh); \
	{ \
		echo "Waiting for container $$CONTAINER_ID..."; \
		docker wait "$$CONTAINER_ID"; \
		docker logs "$$CONTAINER_ID" > "${HOST_TEMP_PATH}/container.log" 2>&1; \
		echo "=== SCREEN LOG ==="; \
		cat "${HOST_TEMP_PATH}/screen.log" 2>/dev/null || echo "Screen log not found"; \
		rm -rf "${HOST_TEMP_PATH}"; \
		echo "QEMU test completed. Press enter"; \
	} &
	@echo "QEMU test started in background"

help:
	@echo "Usage:"
	@echo "  make [targets] [arguments]"
	@echo
	@echo "  docker                 Builds a docker image;"
	@echo "  docker-init-volumes    Initializes docker volumes;"
	@echo "  docker-run-image       Runs builded Yocto image from builded docker image;"
	@echo "  docker-test-image      Tests builded Yocto image from builded docker image;"
	@echo "  help                   Displays information about all available targets."


.PHONY: docker docker-init-volumes docker-run-image docker-test-image
